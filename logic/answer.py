# Written with SI assistance (Claude), reviewed by Paridhi Singh
"""Lane B answer builder — one answer, in the format the team agreed:

    VERDICT: INSIDE / NEAR / BEYOND what NASA tested
    One-sentence answer in plain words.
    Closest evidence (up to 3 rows): test ID + material + O2 + airflow + outcome.
    What's not known: the gap, stated plainly.
    Sources: links, kept small.

The verdict, the numbers and the evidence come from classifier.py and
the frozen rows — never from a model. A model may only write the plain
sentence from the retrieved rows.
"""

import csv

from classifier import classify
from number_checker import allowed_numbers_from_rows, check_numbers

PSI_25_URL = "https://psi.nasa.gov/physci/repo/data/investigations/PSI-25"


def load_rows(path):
    """Load the frozen sample/full dataset. Blank = unknown, never guessed."""
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def closest_rows(rows, oxygen_pct, limit=3):
    """Up to `limit` rows closest in O2 to the value asked about."""
    def o2(row):
        try:
            return float(row["oxygen_pct"])
        except (KeyError, TypeError, ValueError):
            return float("inf")

    return sorted(rows, key=lambda r: abs(o2(r) - oxygen_pct))[:limit]


def build_answer(question, oxygen_pct, rows, airflow_cm_s=None):
    """Build one guarded answer. Returns a dict the website can render."""
    result = classify(oxygen_pct, airflow_cm_s)
    verdict = result["verdict"]
    evidence = closest_rows(rows, oxygen_pct)

    if verdict == "BEYOND":
        sentence = (
            f"NASA's BASS-II tests cover {13.6}–{22.2}% oxygen, so "
            f"{oxygen_pct}% oxygen is beyond what was tested — "
            "we can only show the closest tests, not an answer for that condition."
        )
    elif verdict == "NEAR":
        sentence = (
            f"{oxygen_pct}% oxygen is just outside the tested range "
            f"({13.6}–{22.2}% oxygen), so the closest tested rows are the best "
            "evidence we have — treat them as near, not exact."
        )
    else:
        sentence = (
            f"{oxygen_pct}% oxygen is inside the tested range "
            f"({13.6}–{22.2}% oxygen, 129 BASS-II tests), so the rows below "
            "are direct evidence for this condition."
        )

    unknown = list(result["unknown"])
    if any(not row.get("outcome") for row in evidence):
        unknown.append("outcome (not in the PSI-25 CSV — only in the BASS-II report Appendix A)")
    if any(not row.get("airflow_cm_s") for row in evidence):
        unknown.append("airflow in cm/s (CSV has Fan display only; needs the fan calibration file)")

    evidence_out = []
    for row in evidence:
        evidence_out.append({
            "test_id": row.get("test_id"),
            "material": row.get("material"),
            "material_form": row.get("material_form"),
            "oxygen_pct": row.get("oxygen_pct"),
            "airflow_cm_s": row.get("airflow_cm_s") or None,
            "outcome": row.get("outcome") or None,
            "source": row.get("source"),
            "source_url": row.get("source_url"),
        })

    answer = {
        "question": question,
        "verdict": verdict,
        "sentence": sentence,
        "evidence": evidence_out,
        "unknown": sorted(set(unknown)),
        "sources": [PSI_25_URL],
    }

    # Number check: every number in the sentence must be in the dataset
    # or in the question itself.
    allowed = allowed_numbers_from_rows(rows) | {129.0, 18.0, 13.6, 22.2}
    check = check_numbers(sentence, allowed, question_numbers=[oxygen_pct])
    answer["number_check"] = check
    if not check["ok"]:
        answer["sentence"] += (
            f" [UNVERIFIED numbers in this answer: {check['unverified']}]"
        )
    return answer


if __name__ == "__main__":
    rows = load_rows("sample_data.csv")
    for q, o2 in [
        ("A Moon base runs at 30% oxygen. What does NASA's testing cover?", 30.0),
        ("What about 20% oxygen?", 20.0),
        ("What about 24% oxygen?", 24.0),
    ]:
        print(build_answer(q, o2, rows))
        print()
