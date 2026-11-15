# Written with SI assistance (Muse), reviewed by Paridhi Singh
"""Lane B retrieval (RAG) v5 — router reorder + exact lookup + text corpus.

v10 changes (PR #1 review, Daksh, Nov 14):
- MATERIAL_NAMES now includes "silicone" (one of tests.json's
  materials: 4 Saffire II rows, all no_ignition) and "candle" (the
  Japan Wax candle, F4 → Wax). Without these, "Silicone at 22%" and
  "a candle at 17%" fell through to the no-material answer.

v7 changes (Lane A swap, Nov 14):
- No code change: the card corpus now builds from the 200-row
  tests.json when it is next to the repo (cards carry real outcomes
  and sources), so the RAG text for materials is real, not sample.

v5 changes (Daksh, PR #1, third RAG review):
- ROUTER REORDERED. The name check used to run first, so "Is 30%
  oxygen inside our data for PMMA?", "What is the highest oxygen
  for SIBAL?" and "Which SIBAL test had the lowest airflow?" all
  went to RAG. Now unit numbers and highest/lowest are checked
  FIRST, and the name check is for INVESTIGATIONS ONLY — material
  names (PMMA, SIBAL, Nomex) never force RAG.
- WHOLE-WORD, CASE-AWARE NAME MATCHING. "flexible tubing" used to
  return FLEX (substring match) and "the same hardware" used to
  return SAME. Names now match whole tokens only, and the ambiguous
  acronyms SAME and FLEX only match in uppercase (or as SAME-R /
  FLEX-2); lowercase "same" and "flexible" do not match.
- EXACT LOOKUP RETURNS EVERYTHING NAMED. "How does BASS differ from
  BASS-II?" used to return BASS-II only; it now returns BASS and
  BASS-II. Bare "Saffire" returns all three Saffire entries, bare
  "ACME" returns both ACME entries.

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
# Tokens keep hyphens, so "SAME-R", "BASS-II" and "PSI-98" stay one token.
TOKEN_RE = re.compile(r"[A-Za-z0-9]+(?:-[A-Za-z0-9]+)?")
PSI_ID_RE = re.compile(r"psi-(\d+)", re.IGNORECASE)
# Material names (whole-word, case-insensitive) — used for exact lookup
# of cards and for ask()'s material filter, NEVER for the router's
# name check: a material name must not force a question to RAG.
# "silicone" is one of tests.json's materials (4 Saffire II rows, all
# no_ignition); "candle" is the Japan Wax candle (F4), so it maps to
# Wax. Without these, "Silicone at 22%" and "a candle at 17%" fell
# through to the no-material answer (v10).
# "cotton" is the Saffire V-2 cotton jersey (low pressure, 70.7 kPa).
MATERIAL_NAMES = {"nomex": "Nomex", "sibal": "SIBAL", "pmma": "PMMA",
                  "wax": "Wax", "silicone": "Silicone", "candle": "Wax",
                  "cotton": "Cotton"}
# highest/lowest are numeric ONLY with oxygen or airflow in the question.
COMPARATIVE_WORDS = {"highest", "lowest", "maximum", "minimum", "most", "least",
                     "greater", "smaller", "higher", "lower"}
RANGE_WORDS = {"inside", "outside", "beyond", "range", "limit"}
# Words that make an oxygen/airflow question a meaning question
# ("What sensors measured oxygen?" goes to RAG; "What about oxygen
# with no value given?" goes to code and asks for a value).
MEANING_WORDS = {"sensor", "sensors", "objective", "objectives",
                 "investigation", "investigations", "differ", "differs",
                 "difference", "fuel", "fuels", "condition", "conditions",
                 "smoke", "detection", "detect", "detected", "study",
                 "studies", "experiment", "experiments"}

# Cache for the model and for encoded corpus vectors.
_MODEL_CACHE = None
_MODEL_LOADED = False
_EMBEDDING_CACHE = {}


def _question_tokens(question):
    """Whole tokens, hyphens kept: "SAME-R", "BASS-II", "PSI-98" stay
    one token, so "flex" can never match inside "flexible"."""
    return TOKEN_RE.findall(question or "")


def _named_investigations(question):
    """Every INVESTIGATION named in the question, in the order named.

    Whole-token matching, case-aware for the ambiguous acronyms:
    - PSI IDs: PSI-98, PSI-25 (any case).
    - Saffire I/II/III by token; bare "Saffire" means all three.
    - BASS-II and BASS by token.
    - SAME-R by token (any case); SAME only as the uppercase token —
      lowercase "same" ("the same hardware") does not match.
    - FLEX only as the uppercase token, or FLEX-2 — lowercase "flex"
      ("flexible tubing") does not match.
    - ACME by token (any case); bare "ACME" means both ACME entries.
    Material names are NOT here: they never force a question to RAG.
    Returns a list of corpus ids (e.g. ["BASS", "BASS-II"]) or [].
    """
    found = []
    tokens = _question_tokens(question)
    for i, tok in enumerate(tokens):
        low = tok.lower()
        m = re.fullmatch(r"psi-(\d+)", low)
        if m:
            _add(found, f"PSI-{m.group(1)}")
            continue
        if low in ("saffire-i", "saffire-ii", "saffire-iii"):
            _add(found, low.upper())
            continue
        if low == "saffire":
            # "Saffire II" (two words) means SAFFIRE-II only; bare
            # "Saffire" means all three Saffire investigations.
            nxt = tokens[i + 1].lower() if i + 1 < len(tokens) else ""
            if nxt in ("i", "ii", "iii"):
                _add(found, "SAFFIRE-" + nxt.upper())
            else:
                for entry in ("SAFFIRE-I", "SAFFIRE-II", "SAFFIRE-III"):
                    _add(found, entry)
            continue
        if low == "bass-ii":
            _add(found, "BASS-II")
            continue
        if low == "bass":
            _add(found, "BASS")
            continue
        if low == "same-r":
            _add(found, "SAME-R")
            continue
        if tok == "SAME":
            _add(found, "SAME")
            continue
        if tok == "FLEX" or low == "flex-2":
            _add(found, "FLEX")
            continue
        if low in ("acme-bre",):
            _add(found, "ACME-BRE")
            continue
        if low in ("acme-cld",):
            _add(found, "ACME-CLD")
            continue
        if low == "acme":
            for entry in ("ACME-BRE", "ACME-CLD"):
                _add(found, entry)
            continue
    return found


def _add(found, item):
    if item not in found:
        found.append(item)


def _named_material(question):
    """The material named in the question (whole token, any case),
    or None. Used for exact lookup of cards and for ask()'s filter."""
    for tok in _question_tokens(question):
        low = tok.lower()
        if low in MATERIAL_NAMES:
            return MATERIAL_NAMES[low]
    return None


def route(question):
    """Decide how a question should be answered.

    Returns {"path": "code"|"rag", "reason": str}.
    Order matters (v5 fix): unit numbers and highest/lowest are
    checked FIRST, because a material name in the question used to
    send "Is 30% oxygen inside our data for PMMA?" to RAG. The name
    check is for investigations only.
    "code" = a number with a unit, or a highest/lowest question about
    oxygen or airflow: use ask() in answer.py. "rag" = everything
    else, including PSI IDs and investigation names.
    """
    q = (question or "").lower()
    words = set(re.findall(r"[a-z]+", q))

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
    if ("oxygen" in words or "airflow" in words or "flow" in words) and not (words & MEANING_WORDS):
        return {
            "path": "code",
            "reason": "The question is about oxygen or airflow but gives no value — code asks for one (NEED_OXYGEN) instead of guessing from text.",
        }
    if _named_investigations(question):
        return {
            "path": "rag",
            "reason": "The question names an investigation (PSI ID or name) — that is a meaning question, answered from the text corpus.",
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
    """Return EVERY corpus entry named in the question (PSI IDs,
    investigation names, material names), in the order named.
    "How does BASS differ from BASS-II?" returns BASS and BASS-II,
    not just the first. Runs before embeddings."""
    named = _named_investigations(question)
    material = _named_material(question)
    if material is not None:
        named.append(material)
    if not named:
        return []
    by_id = {entry["id"]: entry for entry in corpus}
    by_psi = {entry["psi_id"]: entry for entry in corpus if entry.get("psi_id")}
    out = []
    for name in named:
        entry = by_id.get(name) or by_psi.get(name)
        if entry is not None and entry not in out:
            out.append(entry)
    return out


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
    if exact:
        return {"match": True,
                "results": [{"entry": e, "score": 1.0, "method": "exact"} for e in exact[:top_k]],
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
        print("  -> answer with ask() in answer.py, not retrieval.")
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
        "Is 30% oxygen inside our data for PMMA?",
        "What is the highest oxygen for SIBAL?",
        "Which SIBAL test had the lowest airflow?",
        "What does PSI-25 test?",
        "Which investigation is PSI-98?",
        "Tell me about SAME-R",
        "How does BASS differ from BASS-II?",
        "What is the same hardware used in these tests?",
        "What about flexible tubing?",
        "Which investigation is most relevant for fire safety?",
        "What sensors measured oxygen?",
        "What is the objective of the Saffire investigations, and how do they differ from BASS-II?",
        "Which investigation studies smoke detection?",
        "What is the best pizza topping?",
    ]:
        print_results(question, retrieve(question, rows))
