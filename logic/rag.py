# Written with SI assistance (Muse), reviewed by Paridhi Singh
"""Lane B retrieval (RAG) v3 — router + text corpus.

v3 changes (Daksh, PR #1):
- ROUTER before retrieval. Questions about highest / lowest / "is X
  inside our data" go to CODE (sort or classify), not to RAG —
  embeddings cannot compare numbers. RAG only picks rows or text by
  meaning. The number checker still runs on the final answer.
- RAG now points at TEXT, not the 6 sample rows: the corpus is the
  investigations table (investigations.csv, 8 rows: objective, fuels,
  conditions, sensors, how each investigation differs) plus the
  material cards (cards.py). NASA's challenge notes ask about
  objectives, fuels, conditions, sensors and how investigations
  differ — those are text questions, and this is the corpus for them.
- EMBEDDINGS ARE CACHED: row texts are encoded once per process
  (the model was already cached; now the vectors are too).
- SCORE CUTOFF: when the best embedding score is below CUTOFF, the
  answer is "no match in our data" instead of the least-bad row.
  CUTOFF is 0.30 — a starting value, tune it once the full corpus lands.
- Every retrieved item carries its source (PSI investigation page or
  the PSI-25 page), so every answer can cite it.

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
    "and", "or", "to", "so", "it", "its", "this", "that", "than",
}

# Question words that mean "compare numbers" — those go to code, never RAG.
# "best"/"worst" are deliberately NOT here: they are opinion words, and
# they misrouted an off-topic question ("best pizza topping") to code.
NUMERIC_WORDS = {
    "highest", "lowest", "maximum", "minimum", "most", "least",
    "greater", "smaller", "higher", "lower", "inside", "outside",
    "beyond", "range", "limit",
}
NUMBER_RE = re.compile(r"\d+(?:\.\d+)?\s*(%|cm/s|psi|kpa)?", re.IGNORECASE)

# Cache for the model and for encoded corpus vectors.
_MODEL_CACHE = None
_MODEL_LOADED = False
_EMBEDDING_CACHE = {}


def route(question):
    """Decide how a question should be answered.

    Returns {"path": "code"|"rag", "reason": str}.
    "code" = numeric comparison or a verdict about the tested range:
    use classify()/closest_rows() in answer.py. "rag" = meaning question:
    use retrieve() on the text corpus.
    """
    q = (question or "").lower()
    words = set(re.findall(r"[a-z]+", q))
    if words & NUMERIC_WORDS or NUMBER_RE.search(q):
        return {
            "path": "code",
            "reason": "The question compares numbers or asks about the tested range — that goes to code (sort or classify), not to embeddings.",
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
    sensors, how each investigation differs)."""
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def investigation_text(inv):
    """One paragraph per investigation — this is what gets embedded."""
    return (
        f"{inv['investigation']} ({inv['psi_id']}): {inv['objective']}. "
        f"Fuels: {inv['fuels']}. Conditions: {inv['conditions']}. "
        f"Sensors: {inv['sensors']}. How it differs: {inv['how_it_differs']}."
    )


def build_corpus(rows):
    """The text corpus: one entry per investigation, plus one per
    material card. Each entry carries its source for citations."""
    corpus = []
    for inv in load_investigations():
        corpus.append({
            "id": inv["id"],
            "kind": "investigation",
            "text": investigation_text(inv),
            "source": inv["source_url"],
        })
    for card in build_cards(rows):
        corpus.append({
            "id": card["material"],
            "kind": "material_card",
            "text": (
                f"{card['material']} ({card['material_form']}): "
                f"{card['what_happened']} {card['why_it_matters']} "
                f"Next action: {card['next_action']} "
                f"Not known: {card['not_known']}"
            ),
            "source": card["source_url"],
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


def retrieve(question, rows, top_k=3, cutoff=CUTOFF):
    """Retrieve the top_k corpus entries for a free-text question.

    Returns {"match": bool, "results": [...]}. When the best score is
    below `cutoff`, match is False and results is empty — the answer
    must say "no match in our data", not show the least-bad row.
    Each result carries its source, so the answer can cite it.
    """
    corpus = build_corpus(rows)
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
        print("  -> answer with classify()/closest_rows() in answer.py, not retrieval.")
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
        "What is the objective of the Saffire investigations, and how do they differ from BASS-II?",
        "Which investigation studies smoke detection?",
        "What is the best pizza topping?",
    ]:
        print_results(question, retrieve(question, rows))
