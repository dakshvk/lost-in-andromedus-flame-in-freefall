# Written with SI assistance (Claude Code), reviewed by Daksh Kumar
"""Lane C API (option A): a small FastAPI app around Lane B's ask().

Run from the repo root:
    python3 web/export_data.py          # refresh web/data/ first
    uvicorn api.app:app --reload --port 8000

Endpoints:
    GET  /api/health             counts, and whether the data loaded
    POST /api/ask                {"question": "..."} -> Lane B's answer
    GET  /api/data/{name}        one of the exported web/data/*.json files
    GET  /                       the static site in web/ (once it exists)

The question text is untrusted input: it is length-limited and only
ever passed to Lane B's deterministic code (router, classifier, number
checker, retrieval). No language model writes any answer here.
"""

import json
import os
import sys
import threading

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
LOGIC = os.path.join(ROOT, "logic")
WEB = os.path.join(ROOT, "web")
WEB_DATA = os.path.join(WEB, "data")
TESTS_JSON = os.path.join(ROOT, "data", "tests.json")
# ROOT so `logic.*` imports resolve; LOGIC so Lane B's own flat imports still work.
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
if LOGIC not in sys.path:
    sys.path.insert(0, LOGIC)

# Import Lane B's modules by their plain names (answer, cards, rag), exactly as
# Lane B's own code does. Importing them as logic.answer, logic.rag and so on loads
# every module twice, so the search model loaded at start-up is not the one real
# questions use. The editor finds them through pyrightconfig.json and .pylintrc.
from answer import ask, dataset_stats_tests_json  # noqa: E402
from cards import rows_from_tests_json  # noqa: E402
from rag import _named_material, retrieve  # noqa: E402

DATA_FILES = {"tests", "cards", "experiments", "investigations",
              "limits", "demo_answers", "meta"}
MAX_QUESTION_CHARS = 300

# Loaded once at startup: 200 rows is small, and every answer reads them.
ROWS = rows_from_tests_json(TESTS_JSON)
STATS = dataset_stats_tests_json(TESTS_JSON)

def _warm_up():
    """The first text question loads the language model (about 10 seconds).
    Do that now, in the background, so a live demo never waits for it."""
    try:
        retrieve("warm up", ROWS)
    except Exception as err:  # never stop the server over this
        print("warm-up skipped:", err)


threading.Thread(target=_warm_up, daemon=True).start()

app = FastAPI(title="Will it burn in a Moon base?", version="0.1.0")
# Public, read-only API with no cookies or accounts, so any origin may call it
# (the static site may be hosted somewhere else than the API).
app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_methods=["GET", "POST"], allow_headers=["Content-Type"])


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=MAX_QUESTION_CHARS)


@app.get("/api/health")
def health():
    return {"ok": True, "rows": len(ROWS), "total_tests": STATS["total_tests"],
            "data_exported": os.path.exists(os.path.join(WEB_DATA, "meta.json"))}


@app.post("/api/ask")
def ask_endpoint(body: AskRequest):
    question = body.question.strip()
    if not question:
        raise HTTPException(status_code=422, detail="Question is empty.")
    result = ask(question, ROWS, stats=STATS)
    # The material the question names (or None), so the page can open
    # that material's card and graph next to the answer.
    result["material"] = _named_material(question)
    return result


@app.get("/api/data/{name}")
def data_file(name: str):
    if name not in DATA_FILES:
        raise HTTPException(status_code=404, detail=f"Unknown data file: {name}")
    path = os.path.join(WEB_DATA, f"{name}.json")
    if not os.path.exists(path):
        raise HTTPException(status_code=503,
                            detail="Data not exported yet: run python3 web/export_data.py")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# The static site last, so /api/* routes win. html=True serves index.html at /.
if os.path.isdir(WEB):
    app.mount("/", StaticFiles(directory=WEB, html=True), name="web")
