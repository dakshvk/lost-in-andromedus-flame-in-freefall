# Written with SI assistance (Muse), reviewed by Paridhi Singh
"""Lane B retrieval (RAG) v4 — router fix + exact lookup + text corpus.

v4 changes (Daksh, PR #1, second RAG review):
- ROUTER FIXED. The old router sent ANY digit to code, so "What does
  PSI-25 test?" and "Which investigation is PSI-98?" went to the wrong
  path, and so did "most relevant", "range of fuels" and "inside
  Cygnus". Now: a number only counts if it has a unit (%, cm/s, psi,
  kPa); PSI IDs (PSI-25, PSI-98) and investigation names (Saffire,
  BASS, SAME, FLEX, ACME, Nomex, SIBAL, PMMA) are meaning questions;
  highest/lowest only count as numeric when oxygen or airflow is
  mentioned too.
- EXACT LOOKUP BEFORE EMBEDDINGS. "Tell me about SAME-R" used to
  return no match and "PSI-98" used to return Saffire II. Now a PSI
  ID or an investigation name in the question returns that exact entry
  first, with method "exact", before embeddings run.
- The corpus is the investigations table (investigations.csv — now 10
  rows: BASS PSI-26 added; ACME is PSI-20 and PSI-21, not PSI-10)
  plus the material cards. Objective and sensor text sources are
  recorded per row in the table's source_notes column.
- EMBEDDINGS ARE CACHED per process and there is a 0.30 score cutoff:
  off-topic questions answer "no match in our data".
- Every retrieved item carries its source, so every answer can cite it.

The model is sentence-transformers/all-MiniLM-L6-v2 — free, runs on
your own computer, no API key, no internet needed after the first
download (~90 MB, one time). If it is not installed yet, this file
still runs on a keyword fallback so you can test the shape of it:
    pip install sentence-transformers
"""

import csv
import math
import re

from answer import load_rows
from cards import build_cards

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
CUTOFF = 0.30

# Words that carry no meaning for matching (fallback only).
STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were", "what", "which", "who",
    "how", "does", "do", "did", "at", "in", "on", "of", "for", "with",
    "and", "or", "to", "so", "it", "its", "this", "that", "than", "from",
    "they", "them", "he", "she", "we", "you", "have", "has", "had", "be",
    "been", "being", "will", "would", "can", "could", "should", "may",
    "might", "must", "not", "no", "if", "then", "when", "where", "why",
    "all", "any", "each", "both", "more", "most", "other", "some", "such",
    "only", "own", "same", "too", "very", "just", "also",
}

# A number only counts as numeric if it carries a unit.
UNIT_NUMBER_RE = re.compile(r"\d+(?:\.\d+)?\s*(%|cm/s|psi|kpa)", re.IGNORECASE)
# PSI IDs and investigation names are meaning, never code.
PSI_ID_RE = re.compile(r"psi[-\s]?(\d+)", re.IGNORECASE)
INVESTIGATION_NAMES = {
    "saffire": "SAFFIRE",
    "bass-ii": "BASS-II",
    "bass": "BASS",
    "same-r": "SAME-R",
    "same": "SAME",
    "flex": "FLEX",
    "acme": "ACME",
    "nomex": "Nomex",
    "sibal": "SIBAL",
    "pmma": "PMMA",
}
# highest/lowest are numeric ONLY with oxygen or airflow in the question.
COMPARATIVE_WORDS = {"highest", "lowest", "maximum", "minimum", "most", "least",
                     "greater", "smaller", "higher", "lower"}
RANGE_WORDS = {"inside", "outside", "beyond", "range", "limit"}

# Cache for the model and for encoded corpus vectors.
_MODEL_CACHE = None
_MODEL_LOADED = False
_EMBEDDING_CACHE = {}


def _has_psi_id_or_name(question):
    """Return the corpus id named in the question, if any (PSI-98,
    SAME-R, Saffire II, BASS-II, ...), else None."""
    q = (question or "").lower()
    m = PSI_ID_RE.search(q)
    if m:
        return f"PSI-{m.group(1)}"
    for name in sorted(INVESTIGATION_NAMES, key=len, reverse=True):
        if name in q:
            return INVESTIGATION_NAMES[name]
    return None


def route(question):
    """Decide how a question should be answered.

    Returns {"path": "code"|"rag", "reason": str}.
    "code" = a number with a unit, or a highest/lowest question about
    oxygen or airflow: use classify()/closest_rows()/max_oxygen() in
    answer.py. "rag" = everything else, including PSI IDs,
    investigation names, and words like "most relevant" or "inside
    Cygnus" on their own.
    """
    q = (question or "").lower()
    words = set(re.findall(r"[a-z]+", q))

    if _has_psi_id_or_name(question):
        return {
            "path": "rag",
            "reason": "The question names an investigation (PSI ID or name) — that is a meaning question, answered from the text corpus.",
        }
    if UNIT_NUMBER_RE.search(q):
        return {
            "path": "code",
            "reason": "The question has a number with a unit (%, cm/s, psi, kPa) — that goes to code, not to embeddings.",
        }
    if (words & COMPARATIVE_WORDS) and ("oxygen" in words or "airflow" in words or "flow" in words):
        return {
            "path": "code",
            "reason": "The question compares oxygen or airflow (highest/lowest) — that goes to code, which can actually compute a max or min.",
        }
    if (words & RANGE_WORDS) and ("oxygen" in words or "airflow" in words or "flow" in words or "data" in words):
        return {
            "path": "code",
            "reason": "The question asks about the tested range for oxygen or airflow — that goes to code (classify).",
        }
    return {
        "path": "rag",
        "reason": "The question is about meaning (objectives, fuels, conditions, sensors, how investigations differ) — that goes to retrieval.",
    }


def row_text(row):
    """One short sentence per sample row — used for row retrieval."""
    parts = [f"{row.get('material', '')} {row.get('material_form', '')}".strip()]
    parts.append(f"test {row.get('test_id', '')}")
    if row.get("oxygen_pct") not in (None, ""):
        parts.append(f"{row['oxygen_pct']}% oxygen")
    if row.get("airflow_cm_s") not in (None, ""):
        flow = f"airflow {row['airflow_cm_s']} cm/s"
        if row.get("airflow_end_cm_s") not in (None, ""):
            flow += f" falling to {row['airflow_end_cm_s']} cm/s"
        parts.append(flow)
    return ", ".join(p for p in parts if p) + "."


def load_investigations(path="investigations.csv"):
    """Load the investigations table (objective, fuels, conditions,
    sensors, how each investigation differs, and source_notes)."""
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def investigation_text(inv):
    """One paragraph per investigation — this is what gets embedded.
    The short id (BASS-II, SAFFIRE-I, ...) is in the text so a question
    naming it matches the right entry."""
    return (
        f"{inv['id']} — {inv['investigation']} ({inv['psi_id']}): {inv['objective']}. "
        f"Fuels: {inv['fuels']}. Conditions: {inv['conditions']}. "
        f"Sensors: {inv['sensors']}. How it differs: {inv['how_it_differs']}."
    )


def build_corpus(rows):
    """The text corpus: one entry per investigation, plus one per
    material card. Each entry carries its source for citations.

    The cards are built from the FULL 129-row CSV when it is next to
    the repo, so RAG answers never quote the 6-row sample's "2 tests"
    counts; otherwise they fall back to the rows given, and say so in
    their source note."""
    import os
    from cards import build_cards, rows_from_full_csv

    corpus = []
    for inv in load_investigations():
        corpus.append({
            "id": inv["id"],
            "psi_id": inv["psi_id"],
            "kind": "investigation",
            "text": investigation_text(inv),
            "source": inv["source_url"],
            "source_notes": inv.get("source_notes", ""),
        })
    full_csv = os.path.join(os.path.dirname(__file__), "..", "data", "raw",
                            "PSI-25_Experimental table_BASS-II.csv")
    if os.path.exists(full_csv):
        card_rows = rows_from_full_csv(full_csv)
        card_note = "Built from the full PSI-25 CSV by cards.py"
    else:
        card_rows = rows
        card_note = "Built from the 6-row sample by cards.py — not dataset numbers"
    for card in build_cards(card_rows):
        # The corpus card text leaves out what_happened's "Tested in
        # BASS-II" line: it made every card match any question that
        # mentions BASS-II, crowding out the investigation entries.
        # The test counts and oxygen ranges stay in why_it_matters.
        corpus.append({
            "id": card["material"],
            "psi_id": None,
            "kind": "material_card",
            "text": (
                f"{card['material']} ({card['material_form']}): "
                f"{card['why_it_matters']} "
                f"Next action: {card['next_action']} "
                f"Not known: {card['not_known']}"
            ),
            "source": card["source_url"],
            "source_notes": card_note,
        })
    return corpus


def _words(text):
    # Single-letter tokens are dropped: "NASA's" splits into "nasa" + "s",
    # and "cm/s" splits into "cm" + "s" — that stray "s" would match
    # everything and pollute the score.
    return {
        w for w in re.findall(r"[a-z0-9.]+", (text or "").lower())
        if w not in STOPWORDS and len(w) > 1
    }


def _cosine(a, b):
    """How similar two lists of numbers are: 1 = same direction, 0 = unrelated."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _load_model():
    """Return the embedding model, or None if it is not installed yet.
    Loaded once and cached."""
    global _MODEL_CACHE, _MODEL_LOADED
    if not _MODEL_LOADED:
        _MODEL_LOADED = True
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            _MODEL_CACHE = None
        else:
            _MODEL_CACHE = SentenceTransformer(MODEL_NAME)
    return _MODEL_CACHE


def _encode(texts):
    """Encode a list of texts, caching the vectors per process so a
    second question does not re-encode the whole corpus."""
    key = tuple(texts)
    if key not in _EMBEDDING_CACHE:
        model = _load_model()
        if model is None:
            _EMBEDDING_CACHE[key] = None
        else:
            _EMBEDDING_CACHE[key] = model.encode(list(texts), convert_to_numpy=True)
    return _EMBEDDING_CACHE[key]


def _exact_lookup(question, corpus):
    """Return the corpus entry named in the question (PSI ID or
    investigation/material name), or None. Runs before embeddings."""
    named = _has_psi_id_or_name(question)
    if named is None:
        return None
    for entry in corpus:
        if entry.get("psi_id") == named or entry["id"] == named:
            return entry
    return None


def retrieve(question, rows, top_k=3, cutoff=CUTOFF):
    """Retrieve the top_k corpus entries for a free-text question.

    Returns {"match": bool, "results": [...]}. An exact ID/name match
    returns first with method "exact". Otherwise, when the best
    embedding score is below `cutoff`, match is False and results is
    empty — the answer must say "no match in our data", not show the
    least-bad row. Each result carries its source, so the answer can
    cite it.
    """
    corpus = build_corpus(rows)

    exact = _exact_lookup(question, corpus)
    if exact is not None:
        return {"match": True,
                "results": [{"entry": exact, "score": 1.0, "method": "exact"}],
                "method": "exact", "best_score": 1.0}

    texts = [entry["text"] for entry in corpus]
    model = _load_model()

    if model is not None:
        vectors = _encode(texts)
        question_vector = model.encode([question], convert_to_numpy=True)[0]
        scored = [
            {"entry": entry, "score": float(_cosine(question_vector, vec)), "method": "embedding"}
            for entry, vec in zip(corpus, vectors)
        ]
    else:
        # Fallback: count shared meaningful words. Same shape, weaker matching.
        question_words = _words(question)
        scored = [
            {"entry": entry, "score": float(len(question_words & _words(entry["text"]))), "method": "keyword"}
            for entry in corpus
        ]

    scored.sort(key=lambda s: s["score"], reverse=True)
    best = scored[0]["score"] if scored else 0.0
    # The cutoff applies to embedding scores (0–1). The keyword fallback
    # uses word counts, so its cutoff is 1 shared word.
    threshold = cutoff if model is not None else 1.0
    if best < threshold:
        return {"match": False, "results": [], "method": scored[0]["method"] if scored else "none", "best_score": best}
    return {"match": True, "results": scored[:top_k], "method": scored[0]["method"], "best_score": best}


def print_results(question, outcome):
    """Print what the router and retrieval decided, the way the
    website's answer panel will use them."""
    routing = route(question)
    print(f"Q: {question}")
    print(f"Route: {routing['path']} — {routing['reason']}")
    if routing["path"] == "code":
        print("  -> answer with classify()/closest_rows()/max_oxygen() in answer.py, not retrieval.")
        print()
        return
    if not outcome["match"]:
        print(f"No match in our data (best score {outcome['best_score']:.3f}, cutoff {CUTOFF}).")
        print()
        return
    print(f"(retrieved with: {outcome['method']})")
    for item in outcome["results"]:
        entry = item["entry"]
        print(f"  {entry['id']} [{entry['kind']}] (score {item['score']:.3f})")
        print(f"    {entry['text'][:160]}...")
        print(f"    Source: {entry['source']}")
    print()


if __name__ == "__main__":
    rows = load_rows("sample_data.csv")
    for question in [
        "Which material was tested at the highest oxygen?",
        "Is 30% oxygen inside our data?",
        "What does PSI-25 test?",
        "Which investigation is PSI-98?",
        "Tell me about SAME-R",
        "Which investigation is most relevant for fire safety?",
        "What sensors measured oxygen?",
        "What is the objective of the Saffire investigations, and how do they differ from BASS-II?",
        "Which investigation studies smoke detection?",
        "What is the best pizza topping?",
    ]:
        print_results(question, retrieve(question, rows))
