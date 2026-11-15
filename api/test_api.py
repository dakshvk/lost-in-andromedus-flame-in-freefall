# Written with SI assistance (Claude Code), reviewed by Daksh Kumar
"""Tests for the Lane C API and the web/data export.

Run from the repo root:
    python3 -m pytest -q api
"""

import os
import sys

import pytest
from fastapi.testclient import TestClient

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "web"))

import export_data  # noqa: E402

export_data.main()  # the API serves web/data/, so export it first

from api.app import app  # noqa: E402

client = TestClient(app)


def ask(question):
    res = client.post("/api/ask", json={"question": question})
    assert res.status_code == 200, res.text
    return res.json()


def test_health():
    body = client.get("/api/health").json()
    assert body["ok"] is True
    assert body["rows"] == 200
    assert body["data_exported"] is True


def test_pmma_30_percent_is_beyond_with_checked_numbers():
    out = ask("Will PMMA burn at 30% oxygen?")
    assert out["material"] == "PMMA"
    assert out["answer"]["verdict"] == "BEYOND"
    assert out["answer"]["number_check"]["ok"] is True
    assert "Saffire V" in out["answer"]["nearest_evidence"]["text"]


def test_airflow_outside_pmma_range_is_beyond():
    out = ask("Will PMMA burn at 20% oxygen and 45 cm/s airflow?")
    assert out["answer"]["verdict"] == "BEYOND"


def test_cotton_points_to_saffire_v2():
    out = ask("Will cotton burn at 26% oxygen?")
    assert out["material"] == "Cotton"
    assert [e["test_id"] for e in out["answer"]["evidence"]] == ["V-2"]


def test_text_question_uses_retrieval():
    out = ask("Which investigation studies smoke detection?")
    assert out["path"] == "rag"
    assert out["retrieval"]["match"] is True
    assert out["material"] is None


def test_off_topic_question_has_no_match():
    out = ask("What is the best pizza topping?")
    assert out["retrieval"]["match"] is False


@pytest.mark.parametrize("question", ["", "   ", "x" * 301])
def test_bad_questions_are_rejected(question):
    assert client.post("/api/ask", json={"question": question}).status_code == 422


def test_unknown_data_file_is_404():
    assert client.get("/api/data/secrets").status_code == 404


def test_data_files_and_counts():
    meta = client.get("/api/data/meta").json()
    assert meta["tests"] == 200
    assert meta["experiments"] == 24
    assert meta["investigations"] == 10
    for name in ["tests", "cards", "experiments", "investigations", "limits", "demo_answers"]:
        assert client.get(f"/api/data/{name}").status_code == 200


def test_cards_match_the_answer_engine():
    cards = client.get("/api/data/cards").json()
    by_name = {c["material"]: c for c in cards["cards"]}
    # Same counts the answers quote: PMMA 102 (no Link rows), 76 known.
    assert by_name["PMMA"]["test_count"] == 102
    assert by_name["PMMA"]["known_outcomes"] == 76
    assert by_name["PMMA"]["airflow_range_cm_s"] == [0.0, 20.0]
    assert by_name["SIBAL"]["test_count"] == 32
    assert by_name["Wax"]["too_few"] is True
    low = [c["material"] for c in cards["low_pressure_group"]["cards"]]
    assert "Cotton (Saffire V, 70.7 kPa)" in low
    assert all("(Saffire V," not in m for m in by_name)


def test_ranking_keeps_reasons_and_note():
    exp = client.get("/api/data/experiments").json()
    assert "team's judgement" in exp["note"]
    top = exp["experiments"][0]
    assert top["psi_id"] == "PSI-25"
    assert sum(b["points"] for b in top["score_breakdown"]) == top["score"]
