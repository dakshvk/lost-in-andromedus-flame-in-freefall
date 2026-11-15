# Written with SI assistance (Muse), reviewed by Paridhi Singh
"""Regenerate demo_answers.json and ask_samples.json from the code.

Run from inside logic/:  python3 generate_samples.py

Uses the full dataset — Lane A's data/tests.json (200 rows) when it
sits next to the repo, else the PSI-25 CSV, else the 6-row sample
(and the note says so). Never type these answers by hand: every
number in them comes from the code, and every answer carries its
number check.
"""

import json
import os

from answer import (
    answer_highest_airflow,
    answer_highest_oxygen,
    answer_lowest_oxygen,
    ask,
    build_answer,
    dataset_stats,
    dataset_stats_tests_json,
    load_rows,
)
from cards import rows_from_full_csv, rows_from_tests_json
from classifier import material_ranges

HERE = os.path.dirname(__file__)
TESTS_JSON = os.path.join(HERE, "..", "data", "tests.json")
FULL_CSV = os.path.join(
    HERE, "..", "data", "raw", "PSI-25_Experimental table_BASS-II.csv")

SAMPLE_QUESTIONS = [
    "What about 20% oxygen?",
    "Is 30% oxygen inside our data for PMMA?",
    "What about oxygen with no value given?",
    "Which material was tested at the highest oxygen?",
    "What is the lowest oxygen tested?",
    "What is the highest airflow tested?",
    "Which SIBAL test had the lowest airflow?",
    "Is 10 cm/s airflow inside our data?",
    "What sensors measured oxygen?",
    "How does BASS differ from BASS-II?",
    "Which investigation studies smoke detection?",
    "What is the best pizza topping?",
]


def load_full_rows():
    """Full rows + stats + a label for the note, preferring tests.json."""
    if os.path.exists(TESTS_JSON):
        return (rows_from_tests_json(TESTS_JSON),
                dataset_stats_tests_json(TESTS_JSON),
                "the 200-row tests.json (Lane A)")
    if os.path.exists(FULL_CSV):
        return (rows_from_full_csv(FULL_CSV),
                dataset_stats(FULL_CSV),
                "the full 129-row PSI-25 CSV")
    sample = load_rows("sample_data.csv")
    return sample, None, "the 6-row sample only"


def main():
    full_rows, stats, label = load_full_rows()
    ranges = material_ranges(full_rows)
    q1 = build_answer(
        "A Moon base runs at 30% oxygen. What does NASA testing cover?",
        30.0, full_rows, stats=stats)
    q2 = build_answer(
        "Do materials burn as well in microgravity as on Earth?",
        21.0, full_rows, stats=stats)
    pmma_max = ranges["PMMA"][1]
    sibal_max = ranges["SIBAL"][1]
    q3 = {
        "question": "Compare PMMA film with SIBAL cloth.",
        "pmma": build_answer(
            "Compare PMMA film with SIBAL cloth.",
            pmma_max, full_rows, material="PMMA", stats=stats),
        "sibal": build_answer(
            "Compare PMMA film with SIBAL cloth.",
            sibal_max, full_rows, material="SIBAL", stats=stats),
    }
    demo = {
        "note": ("Demo answers, generated from the code (v7, Nov 14, 2026) "
                 f"— not typed by hand. All six use {label}."),
        "answers": [
            q1, q2, q3,
            answer_highest_oxygen(full_rows, stats=stats),
            answer_lowest_oxygen(full_rows, stats=stats),
            answer_highest_airflow(full_rows, stats=stats),
        ],
    }
    with open("demo_answers.json", "w", encoding="utf-8") as f:
        json.dump(demo, f, indent=1)
    samples = {
        "note": ("Sample ask() responses for the web lane, one per answer "
                 f"type. Generated from {label} with v7 code, Nov 14, 2026. "
                 "RAG samples use the keyword fallback in this file (no "
                 "model installed here); on a machine with "
                 "sentence-transformers installed the same ask() call "
                 "returns embedding retrieval instead."),
        "samples": [{"question": q, **ask(q, full_rows, stats=stats)}
                    for q in SAMPLE_QUESTIONS],
    }
    with open("ask_samples.json", "w", encoding="utf-8") as f:
        json.dump(samples, f, indent=1)
    for a in demo["answers"]:
        if "sentence" in a:
            print(a["question"], "->", a["sentence"][:100],
                  "| check:", a["number_check"])
        else:
            print(a["question"], "-> PMMA:", a["pmma"]["sentence"][:80],
                  "| SIBAL:", a["sibal"]["sentence"][:80])
    bad = [a for a in demo["answers"]
           if "number_check" in a and not a["number_check"]["ok"]]
    bad += [s for s in samples["samples"]
            if s.get("answer") and not s["answer"]["number_check"]["ok"]]
    print("number checks failing:", len(bad))
    return demo, samples


if __name__ == "__main__":
    main()
