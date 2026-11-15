# Written with SI assistance (Muse), reviewed by Paridhi Singh
"""Lane B answer builder — one answer, in the format the team agreed:

    VERDICT: INSIDE / NEAR / BEYOND what NASA tested
    One-sentence answer in plain words.
    Closest evidence (up to 3 rows): test ID + material + O2 + airflow + outcome.
    What's not known: the gap, stated plainly.
    Sources: links, kept small.
    Gravity note: every answer says the tests were in microgravity.

v2 changes (PR #1 review, Daksh):
- closest_rows() filters by material first when one is given, so a
  SIBAL question no longer returns PMMA rows.
- A missing oxygen value returns verdict NEED_OXYGEN and an answer
  that asks for a value, instead of BEYOND.
- Stats (129 tests, 13.6–22.2% O2, 18 rows above 21%) are DERIVED
  from the full PSI-25 CSV by dataset_stats(), never typed in.
  The sample file alone must not be used for those numbers.
- "Airflow is unknown" is only said when the evidence rows really
  have no airflow. Airflow now comes from the PSI "Air display"
  column (transducer reading in cm/s); flow_start is the first
  number in that column, flow_end the second when present (T25: 5 -> 2.5).
- Every answer carries the gravity note: the data is microgravity
  (ISS); the Moon is about one-sixth Earth's gravity and pressure
  differs, so a Moon-base condition is not covered by these tests.
"""

import csv

from classifier import classify, dataset_range, material_ranges
from number_checker import allowed_numbers_from_rows, check_answer_numbers

PSI_25_URL = "https://psi.nasa.gov/physci/repo/data/investigations/PSI-25"
GRAVITY_NOTE = (
    "These tests were in microgravity on the ISS. The Moon is about "
    "one-sixth Earth's gravity, and pressure differs, so a Moon-base "
    "condition is not covered by these tests."
)


def load_rows(path):
    """Load the frozen sample/full dataset. Blank = unknown, never guessed."""
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def dataset_stats(full_csv_path):
    """Derive the dataset stats from the full PSI-25 CSV.

    Returns {"total_tests", "o2_min", "o2_max", "rows_above_21"}.
    Read the real file — do not type these numbers in.
    """
    with open(full_csv_path, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    o2 = []
    for row in rows:
        try:
            o2.append(float(row["Calibrated  initial O2 % by vol "]))
        except (KeyError, TypeError, ValueError):
            continue
    return {
        "total_tests": len(rows),
        "o2_min": min(o2),
        "o2_max": max(o2),
        "rows_above_21": sum(1 for v in o2 if v > 21.0),
    }


def closest_rows(rows, oxygen_pct, limit=3, material=None):
    """Up to `limit` rows closest in O2. When a material is given,
    only rows for that material are considered first."""
    def o2(row):
        try:
            return float(row["oxygen_pct"])
        except (KeyError, TypeError, ValueError):
            return float("inf")

    pool = rows
    if material:
        same_material = [r for r in rows if r.get("material") == material]
        if same_material:
            pool = same_material
    return sorted(pool, key=lambda r: abs(o2(r) - oxygen_pct))[:limit]


def build_answer(question, oxygen_pct, rows, airflow_cm_s=None, material=None, stats=None):
    """Build one guarded answer. Returns a dict the website can render."""
    result = classify(oxygen_pct, airflow_cm_s, material=material, rows=rows)
    verdict = result["verdict"]

    if verdict == "NEED_OXYGEN":
        return {
            "question": question,
            "verdict": verdict,
            "sentence": "I need an oxygen value to answer that — what oxygen level are you asking about?",
            "evidence": [],
            "unknown": ["oxygen_pct"],
            "gravity_note": GRAVITY_NOTE,
            "sources": [PSI_25_URL],
            "number_check": {"ok": True, "unverified": []},
        }

    evidence = closest_rows(rows, oxygen_pct, material=material)
    stats_from_sample = stats is None
    stats = stats or {
        "total_tests": len(rows),
        "o2_min": dataset_range(rows)[0],
        "o2_max": dataset_range(rows)[1],
        "rows_above_21": sum(
            1 for r in rows
            if r.get("oxygen_pct") not in (None, "") and float(r["oxygen_pct"]) > 21.0
        ),
    }
    o2_min, o2_max = stats["o2_min"], stats["o2_max"]
    total = stats["total_tests"]

    # When a material is given, the sentence must quote THAT material's
    # tested range — quoting the overall range would contradict the verdict
    # (e.g. 14% O2 is inside 13.6–22.2% overall, but BEYOND for SIBAL,
    # whose tested range is 16.4–20.8% in the full data).
    if material and rows:
        per_material = material_ranges(rows)
        if material in per_material:
            r_min, r_max = per_material[material]
            range_text = f"{material} {r_min}–{r_max}% oxygen"
        else:
            range_text = f"{o2_min}–{o2_max}% oxygen"
    else:
        range_text = f"{o2_min}–{o2_max}% oxygen"

    if verdict == "BEYOND":
        sentence = (
            f"NASA's BASS-II tests cover {range_text}, so "
            f"{oxygen_pct}% oxygen is beyond what was tested — "
            "we can only show the closest tests, not an answer for that condition."
        )
    elif verdict == "NEAR":
        sentence = (
            f"{oxygen_pct}% oxygen is just outside the tested range "
            f"({range_text}), so the closest tested rows are the best "
            "evidence we have — treat them as near, not exact."
        )
    else:
        sentence = (
            f"{oxygen_pct}% oxygen is inside the tested range "
            f"({range_text}, {total} BASS-II tests), so the rows below "
            "are direct evidence for this condition."
        )

    # Nearest evidence beyond BASS-II, for Moon-cabin conditions.
    # NASA's challenge notes (per Daksh, Nov 14) put the Moon cabin at
    # 30%+ O2 at about 10 psi, and Saffire V at about 26% O2 at about
    # 71 kPa — the closest published reference, still below the cabin.
    # Saffire IV/V data is NOT in PSI (GIPOC-locked, per Daksh Part 1),
    # so this is cited to NASA's notes, not to a row in our dataset,
    # and its numbers are checked against the notes, not the dataset.
    nearest_evidence = None
    if verdict == "BEYOND" and oxygen_pct is not None and float(oxygen_pct) >= 30.0:
        nearest_evidence = {
            "text": (
                "Nearest evidence beyond BASS-II: Saffire V, at about 26% "
                "oxygen and about 71 kPa — still below a 30%+ oxygen Moon "
                "cabin at about 10 psi."
            ),
            "source": "NASA challenge notes (per Daksh, Nov 14, 2026)",
            "numbers": [26.0, 71.0, 10.0, 30.0],
        }

    unknown = list(result["unknown"])
    if stats_from_sample:
        unknown.append("dataset stats are from the 6-row sample only — the full 129-test CSV was not loaded, so do not quote these as dataset numbers")
    # Only claim airflow is unknown when the evidence rows really lack it.
    if any(not row.get("airflow_cm_s") for row in evidence):
        unknown.append("airflow in cm/s for some evidence rows (no Air display value in the CSV)")
    if any(not row.get("outcome") for row in evidence):
        unknown.append("outcome (not in the PSI-25 CSV — only in the BASS-II report Appendix A)")

    evidence_out = []
    for row in evidence:
        evidence_out.append({
            "test_id": row.get("test_id"),
            "material": row.get("material"),
            "material_form": row.get("material_form"),
            "oxygen_pct": row.get("oxygen_pct"),
            "airflow_cm_s": row.get("airflow_cm_s") or None,
            "airflow_end_cm_s": row.get("airflow_end_cm_s") or None,
            "outcome": row.get("outcome") or None,
            "source": row.get("source"),
            "source_url": row.get("source_url"),
        })

    answer = {
        "question": question,
        "verdict": verdict,
        "sentence": sentence,
        "evidence": evidence_out,
        "nearest_evidence": nearest_evidence,
        "unknown": sorted(set(unknown)),
        "gravity_note": GRAVITY_NOTE,
        "sources": [PSI_25_URL],
    }

    answer["number_check"] = check_answer_numbers(
        sentence, evidence_out, stats, question_oxygen=oxygen_pct
    )
    if not answer["number_check"]["ok"]:
        answer["sentence"] += (
            f" [UNVERIFIED: {answer['number_check']['unverified']}]"
        )
    return answer


if __name__ == "__main__":
    import os

    rows = load_rows("sample_data.csv")
    # Full stats come from the real PSI file when it is next to the repo;
    # otherwise fall back to the sample rows and say so.
    full_csv = os.path.join(os.path.dirname(__file__), "..", "data", "raw",
                            "PSI-25_Experimental table_BASS-II.csv")
    if os.path.exists(full_csv):
        stats = dataset_stats(full_csv)
    else:
        stats = None
        print("(full PSI CSV not found next to the repo — stats from the 6-row sample)")
    for q, o2, mat in [
        ("A Moon base runs at 30% oxygen. What does NASA's testing cover?", 30.0, None),
        ("What about 20% oxygen?", 20.0, None),
        ("What about 24% oxygen?", 24.0, None),
        ("What about 14% oxygen for SIBAL?", 14.0, "SIBAL"),
        ("What about oxygen with no value given?", None, None),
    ]:
        print(build_answer(q, o2, rows, material=mat, stats=stats))
        print()

