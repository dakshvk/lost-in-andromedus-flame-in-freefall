# Written with SI assistance (Muse), reviewed by Paridhi Singh
"""Lane B retrieval (RAG) — find the right rows for a free-text question.

How it works, in plain words:
1. Every row is turned into one short sentence, e.g.
   "PMMA film, test B1, 22.2% oxygen, airflow 5 cm/s."
2. The model turns each sentence — and your question — into a list of
   numbers (an embedding). Sentences that mean similar things get
   numbers that point in a similar direction.
3. We compare directions (cosine similarity) and return the top rows.

The model is sentence-transformers/all-MiniLM-L6-v2 — free, runs on
your own computer, no API key, no internet needed after the first
download (~90 MB, one time).

If the model is not installed yet, this file still runs: it falls back
to keyword matching (shared words between question and row) so you can
test the shape of it. Install the real model with:
    pip install sentence-transformers
Then the same code uses embeddings automatically.

Retrieval only: this file NEVER writes an answer sentence. It returns
rows. The sentence still comes from answer.py's build_answer(), so no
model output can invent a number.
"""

import math
import re

from answer import load_rows

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

# Words that carry no meaning for matching (dropped in the fallback only).
STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were", "what", "which", "who",
    "how", "does", "do", "did", "at", "in", "on", "of", "for", "with",
    "and", "or", "to", "so", "it", "its", "this", "that", "than",
}


def row_text(row):
    """One short sentence per row — this is what gets embedded."""
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


# Cache for the embedding model — loaded once, reused for every question.
_MODEL_CACHE = None
_MODEL_LOADED = False


def _load_model():
    """Return the embedding model, or None if it is not installed yet.

    Loaded once and cached: without the cache the model was re-loaded
    from disk for every question (the "Loading weights" line printed
    three times in the first Mac run).
    """
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


def retrieve(question, rows, top_k=3):
    """Return the top_k rows for a free-text question.

    Returns a list of {"row": ..., "score": float, "method": "embedding"|"keyword"}.
    Scores are cosine similarity (embedding) or shared-word count (keyword).
    """
    texts = [row_text(r) for r in rows]
    model = _load_model()

    if model is not None:
        row_vectors = model.encode(texts, convert_to_numpy=True)
        question_vector = model.encode([question], convert_to_numpy=True)[0]
        scored = [
            {"row": row, "score": float(_cosine(question_vector, vec)), "method": "embedding"}
            for row, vec in zip(rows, row_vectors)
        ]
    else:
        # Fallback: count shared meaningful words. Same shape, weaker matching.
        question_words = _words(question)
        scored = []
        for row, text in zip(rows, texts):
            shared = question_words & _words(text)
            scored.append({"row": row, "score": float(len(shared)), "method": "keyword"})

    scored.sort(key=lambda s: s["score"], reverse=True)
    return scored[:top_k]


def print_results(question, results):
    """Print the retrieved rows the way the website's answer panel will use them."""
    method = results[0]["method"] if results else "none"
    print(f"Q: {question}")
    print(f"(retrieved with: {method})")
    for item in results:
        row = item["row"]
        print(
            f"  {row.get('test_id')} — {row.get('material')} "
            f"{row.get('material_form')}, {row.get('oxygen_pct')}% O2, "
            f"airflow {row.get('airflow_cm_s')} cm/s "
            f"(score {item['score']:.3f})"
        )
    print()


if __name__ == "__main__":
    rows = load_rows("sample_data.csv")
    for question in [
        "Which material was tested at the highest oxygen?",
        "What happened with SIBAL cloth?",
        "A Moon base runs at 30% oxygen — what does NASA's testing cover?",
    ]:
        print_results(question, retrieve(question, rows))
