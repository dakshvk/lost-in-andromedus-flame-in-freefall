# Written with SI assistance (Muse), reviewed by Paridhi Singh
"""Lane B number checker — numbers must belong to the row and unit
they are attached to, not just exist somewhere in the dataset.

v2 changes (PR #1 review, Daksh):
- The old check passed "T25 at 22.2%" (T25 is 20.8%) and "22.2 cm/s"
  (22.2 is an O2 value, not an airflow). Both are now caught:
  a number attached to a test ID must match that row, and a number
  with a unit must match a value in that unit.
- A bare count is no longer allowed just because it equals a row count.
  "6" (the sample size) is not an allowed number on its own; the full
  test count (129) is only allowed in the phrase "129 BASS-II tests".
- check_numbers() is kept for plain existence checks; the answer
  builder uses check_answer_numbers() below, which is row+unit aware.
"""

import re

NUMBER_RE = re.compile(r"\d+(?:\.\d+)?")
# Test IDs like B1, T25, F2, P22a, T28a are identifiers, not quantities.
TEST_ID_RE = re.compile(r"\b[A-Za-z]+\d+[a-z]?\b")
# "T25 at 22.2%" or "B1 at 22.2% oxygen" — a number attached to a test ID.
ROW_NUMBER_RE = re.compile(
    r"\b([A-Za-z]+\d+[a-z]?)\b[^.]{0,40}?(\d+(?:\.\d+)?)\s*(%|cm/s)?"
)
PERCENT_RE = re.compile(r"(\d+(?:\.\d+)?)\s*%")
AIRFLOW_RE = re.compile(r"(\d+(?:\.\d+)?)\s*cm/s")
COUNT_RE = re.compile(r"(\d+)\s+BASS-II tests")


def numbers_in(text):
    """All numbers in a string, as floats (test IDs excluded)."""
    cleaned = TEST_ID_RE.sub(" ", text or "")
    return [float(n) for n in NUMBER_RE.findall(cleaned)]


def check_numbers(text, allowed_numbers, question_numbers=None):
    """Plain existence check: every number in `text` must be in the
    allowed set (dataset numbers) or the question's own numbers."""
    allowed = {float(n) for n in allowed_numbers}
    if question_numbers:
        allowed |= {float(n) for n in question_numbers}
    found = numbers_in(text)
    unverified = sorted({n for n in found if n not in allowed})
    return {"ok": not unverified, "unverified": unverified}


def allowed_numbers_from_rows(rows):
    """Allowed numbers from frozen rows: O2 and airflow values only.
    The row count is deliberately NOT included — see check_answer_numbers."""
    allowed = set()
    for row in rows:
        for key in ("oxygen_pct", "airflow_cm_s", "airflow_end_cm_s"):
            value = row.get(key)
            if value not in (None, ""):
                allowed.add(float(value))
    return allowed


def check_answer_numbers(sentence, evidence, stats, question_oxygen=None):
    """Row+unit-aware check of one answer sentence.

    evidence: the evidence rows the answer cites (dicts with test_id,
        oxygen_pct, airflow_cm_s).
    stats: {"total_tests": 129, "o2_min": 13.6, "o2_max": 22.2,
        "rows_above_21": 18} — derived from the full dataset, not typed in.
    question_oxygen: the O2 value from the question itself.
    Returns {"ok": bool, "unverified": [str, ...]} with a reason per item.
    """
    unverified = []
    by_id = {row["test_id"]: row for row in evidence}
    o2_values = {float(r["oxygen_pct"]) for r in evidence}
    flow_values = {
        float(r["airflow_cm_s"])
        for r in evidence
        if r.get("airflow_cm_s") not in (None, "")
    }

    # 1. A number attached to a test ID must match that row's O2.
    for test_id, value, unit in ROW_NUMBER_RE.findall(sentence or ""):
        row = by_id.get(test_id)
        if row is None:
            continue  # test ID not in this answer's evidence; not our claim
        if unit == "%" and float(value) != float(row["oxygen_pct"]):
            unverified.append(
                f"{test_id} is {row['oxygen_pct']}% oxygen, not {value}%"
            )
        elif unit == "cm/s" and float(value) not in flow_values:
            unverified.append(f"{value} cm/s is not an airflow in the evidence rows")

    # 2. Every "%" number must be the question O2, a range bound, or a row O2.
    allowed_pct = set(o2_values) | {stats["o2_min"], stats["o2_max"]}
    if question_oxygen is not None:
        allowed_pct.add(float(question_oxygen))
    for value in PERCENT_RE.findall(sentence or ""):
        if float(value) not in allowed_pct:
            unverified.append(f"{value}% is not an oxygen value in the data or the question")

    # 3. Every "cm/s" number must be an airflow value in the evidence rows.
    for value in AIRFLOW_RE.findall(sentence or ""):
        if float(value) not in flow_values:
            unverified.append(f"{value} cm/s is not an airflow value in the evidence rows")

    # 4. A bare count is only allowed as "129 BASS-II tests" (the full
    #    dataset count, derived from the data — never the sample size).
    for value in COUNT_RE.findall(sentence or ""):
        if int(value) != stats["total_tests"]:
            unverified.append(f"{value} BASS-II tests is not the dataset count ({stats['total_tests']})")

    return {"ok": not unverified, "unverified": sorted(set(unverified))}
