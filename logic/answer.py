# Written with SI assistance (Muse), reviewed by Paridhi Singh
"""Lane B answer builder — one answer, in the format the team agreed:

    VERDICT: INSIDE / NEAR / BEYOND what NASA tested
    One-sentence answer in plain words.
    Closest evidence (up to 3 rows): test ID + material + O2 + airflow + outcome.
    What's not known: the gap, stated plainly.
    Sources: links, kept small.
    Gravity note: every answer says the tests were in microgravity.

v4 changes (PR #1 review, Daksh):
- answer_highest_oxygen(): the router says "code" for highest/lowest
  questions, so there is now code behind it — max over the full 129
  rows, all 14 ties returned (B1, B2, B3, B4, B5, B7, B12, F1, M1,
  M2, M5, M14, O1, O2), number-checked with the tie count (14)
  allowed as a derived count.
- Saffire V nearest evidence: corrected citation — the numbers come
  from the ICES 2021 Saffire IV/V paper, Table 1 (NTRS 20210011521):
  V-2 cotton 26.2% O2 at 70.7 kPa, V-3 PMMA 25.4% at 71.3 kPa,
  V-4 PMMA 25.7% at 72.6 kPa, all at 20 cm/s flow. Ranges used:
  25.4–26.2% O2, 70.7–72.6 kPa. Moon cabin from the challenge notes:
  30%+ O2 at 10.2 psi or less. "per Daksh" removed; Saffire IV/V
  data is described as "not in the PSI tables we loaded".
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


def max_oxygen(rows):
    """The highest oxygen tested, over the rows given, with ALL ties.

    Returns {"max_oxygen": float, "test_ids": [...], "materials": [...]}.
    Use the full 129 rows, not the 6-row sample: the sample's max is
    also 22.2%, but it only shows 3 of the 14 tests at that level.
    """
    best = None
    for row in rows:
        try:
            value = float(row["oxygen_pct"])
        except (KeyError, TypeError, ValueError):
            continue
        if best is None or value > best:
            best = value
    if best is None:
        return {"max_oxygen": None, "test_ids": [], "materials": []}
    ties = [r for r in rows if r.get("oxygen_pct") not in (None, "") and float(r["oxygen_pct"]) == best]
    return {
        "max_oxygen": best,
        "test_ids": [r["test_id"] for r in ties],
        "materials": sorted({r["material"] for r in ties}),
    }


def answer_highest_oxygen(rows, stats=None):
    """Answer 'which material was tested at the highest oxygen?' with
    code, not embeddings: compute the max over the rows, return all
    ties, and run the number checker on the result. The count of ties
    (14) is derived from the data, so it is an allowed number here."""
    result = max_oxygen(rows)
    if result["max_oxygen"] is None:
        return {
            "question": "Which material was tested at the highest oxygen?",
            "verdict": "NEED_OXYGEN",
            "sentence": "No oxygen values are in the rows I was given.",
            "evidence": [],
            "nearest_evidence": None,
            "unknown": ["oxygen_pct"],
            "gravity_note": GRAVITY_NOTE,
            "sources": [PSI_25_URL],
            "number_check": {"ok": True, "unverified": []},
        }
    n = len(result["test_ids"])
    tests = ", ".join(result["test_ids"])
    sentence = (
        f"The highest oxygen tested is {result['max_oxygen']}%, in {n} tests "
        f"({tests}) — materials: {', '.join(result['materials'])}."
    )
    evidence = [r for r in rows if r.get("test_id") in result["test_ids"]]
    stats = stats or {"total_tests": len(rows), "o2_min": min(float(r["oxygen_pct"]) for r in rows if r.get("oxygen_pct") not in (None, "")), "o2_max": result["max_oxygen"], "rows_above_21": 0}
    check = check_answer_numbers(sentence, evidence, stats, extra_allowed={float(n)})
    return {
        "question": "Which material was tested at the highest oxygen?",
        "verdict": "INSIDE",
        "sentence": sentence,
        "evidence": evidence,
        "nearest_evidence": None,
        "unknown": [],
        "gravity_note": GRAVITY_NOTE,
        "sources": [PSI_25_URL],
        "number_check": check,
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
    # CORRECTION (Daksh, Nov 14): the Saffire V numbers come from the
    # ICES 2021 Saffire IV/V paper, Table 1 (NTRS 20210011521), not
    # from NASA's challenge notes. V-2 cotton 26.2% O2 at 70.7 kPa,
    # V-3 PMMA 25.4% at 71.3 kPa, V-4 PMMA 25.7% at 72.6 kPa, all at
    # 20 cm/s flow. The challenge notes only give the Moon cabin
    # (30%+ O2 at 10.2 psi or less). Saffire IV/V data is not in the
    # PSI tables we loaded, so this is cited to the paper, not to a
    # row in our dataset, and its numbers are checked against the
    # paper, not the dataset.
    nearest_evidence = None
    if verdict == "BEYOND" and oxygen_pct is not None and float(oxygen_pct) >= 30.0:
        nearest_evidence = {
            "text": (
                "Nearest evidence beyond BASS-II: Saffire V tests V-2 to "
                "V-4, 25.4–26.2% oxygen at 70.7–72.6 kPa and 20 cm/s "
                "flow — still below a 30%+ oxygen Moon cabin at 10.2 psi "
                "or less."
            ),
            "source": "Urban et al., ICES 2021, Saffire IV/V paper, Table 1 (NTRS 20210011521)",
            "numbers": [25.4, 26.2, 70.7, 72.6, 20.0, 30.0, 10.2],
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

    # Highest-oxygen question: computed over the full 129 rows, not the sample.
    if os.path.exists(full_csv):
        from cards import rows_from_full_csv
        full_rows = rows_from_full_csv(full_csv)
    else:
        full_rows = rows
    print(answer_highest_oxygen(full_rows, stats=stats))
    print()
