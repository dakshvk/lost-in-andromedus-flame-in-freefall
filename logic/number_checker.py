# Written with SI assistance (Muse), reviewed by Paridhi Singh
"""Lane B number checker — numbers must belong to the row and unit
they are attached to, not just exist somewhere in the dataset.

v9 changes (PR #1 review, Daksh, Nov 14):
- Blank oxygen no longer crashes the checker: the two context-only
  Saffire III rows (100-S1, 100-S2) have flow 30 cm/s but no oxygen
  recorded, and float("") raised ValueError. They are now skipped in
  o2_values and in rule 1's per-row check (as the airflow values
  already were). This surfaced because the 45 cm/s question's
  closest evidence is those two rows plus M2.

v7 changes (Lane A swap, Nov 14):
- Test-ID patterns now swallow suffixed IDs from tests.json:
  B13a-1 (Link replicates), 2-7-PMMA (Saffire II split rows),
  98-S1 / 100-S1 (disambiguated Saffire I/III rows). Without this,
  their digits leaked out as numbers.

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
# Once Lane A's tests.json lands there are also B13a-1 (Link replicates),
# 2-7-PMMA (Saffire II split rows) and 98-S1 / 100-S1 (Saffire I/III
# rows disambiguated across sources) — the pattern must swallow the
# whole ID, or its digits leak out as numbers ("B13a-1" would leave a
# stray "1").
TEST_ID_RE = re.compile(
    r"\b(?:[A-Za-z]+\d+[a-z]?(?:-\d+)?|\d+-\d+-[A-Za-z]+|\d+-[A-Za-z]+\d+[a-z]?)\b")
# "T25 at 22.2%" or "B1 at 22.2% oxygen" — a number attached to a test ID.
ROW_NUMBER_RE = re.compile(
    r"\b((?:[A-Za-z]+\d+[a-z]?(?:-\d+)?|\d+-\d+-[A-Za-z]+|\d+-[A-Za-z]+\d+[a-z]?))\b[^.]{0,40}?(\d+(?:\.\d+)?)\s*(%|cm/s)?"
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


def check_answer_numbers(sentence, evidence, stats, question_oxygen=None, extra_allowed=None, range_bounds=None, flow_bounds=None, question_flow=None, extra_flows=None):
    """Row+unit-aware check of one answer sentence.

    evidence: the evidence rows the answer cites (dicts with test_id,
        oxygen_pct, airflow_cm_s).
    stats: {"total_tests": 129, "o2_min": 13.6, "o2_max": 22.2,
        "rows_above_21": 18} — derived from the full dataset, not typed in.
    question_oxygen: the O2 value from the question itself.
    extra_allowed: numbers derived from the data for this answer only
        (e.g. the count of tests tied at the max oxygen).
    range_bounds: the (low, high) of the oxygen range the sentence
        quotes for a material (e.g. SIBAL 16.4–20.8%) — a range bound
        is an allowed number even when the bound row is not in the
        evidence.
    flow_bounds: the (low, high) of the airflow range the sentence
        quotes (e.g. 0.0–53.0 cm/s) — same rule for airflow.
    Returns {"ok": bool, "unverified": [str, ...]} with a reason per item.
    """
    unverified = []
    by_id = {row["test_id"]: row for row in evidence}
    # Blank oxygen is skipped: the two context-only Saffire III rows
    # (100-S1, 100-S2) have flow 30 cm/s but no oxygen recorded, and
    # float("") crashed the checker (v9: the 45 cm/s question's
    # closest evidence is those two rows plus M2 — with Jenisha's
    # fixed data, O5b/O13a at 5 cm/s, they are the closest by flow).
    o2_values = {float(r["oxygen_pct"]) for r in evidence
                 if r.get("oxygen_pct") not in (None, "")}
    # Airflow values live in BOTH columns: a test's lowest/highest flow
    # can be its flow_end (T4 ends at 1 cm/s, T17 ends at 53 cm/s).
    flow_values = {
        float(r[key])
        for r in evidence
        for key in ("airflow_cm_s", "airflow_end_cm_s")
        if r.get(key) not in (None, "")
    }

    # 1. A number attached to a test ID must match that row's O2.
    for test_id, value, unit in ROW_NUMBER_RE.findall(sentence or ""):
        row = by_id.get(test_id)
        if row is None:
            continue  # test ID not in this answer's evidence; not our claim
        if unit == "%" and row.get("oxygen_pct") not in (None, "") and float(value) != float(row["oxygen_pct"]):
            unverified.append(
                f"{test_id} is {row['oxygen_pct']}% oxygen, not {value}%"
            )
        elif unit == "cm/s" and float(value) not in flow_values:
            unverified.append(f"{value} cm/s is not an airflow in the evidence rows")

    # 2. Every "%" number must be the question O2, a range bound, or a row O2.
    allowed_pct = set(o2_values) | {stats["o2_min"], stats["o2_max"]}
    if range_bounds:
        allowed_pct |= {float(range_bounds[0]), float(range_bounds[1])}
    if question_oxygen is not None:
        allowed_pct.add(float(question_oxygen))
    for value in PERCENT_RE.findall(sentence or ""):
        if float(value) not in allowed_pct:
            unverified.append(f"{value}% is not an oxygen value in the data or the question")

    # 3. Every "cm/s" number must be an airflow value in the evidence
    #    rows, the question's own airflow, a quoted range bound, or a
    #    report number passed in for this answer (e.g. the BASS-II
    #    duct max of about 55 cm/s).
    allowed_flows = set(flow_values)
    if question_flow is not None:
        allowed_flows.add(float(question_flow))
    if flow_bounds:
        allowed_flows |= {float(flow_bounds[0]), float(flow_bounds[1])}
    if extra_flows:
        allowed_flows |= {float(v) for v in extra_flows}
    for value in AIRFLOW_RE.findall(sentence or ""):
        if float(value) not in allowed_flows:
            unverified.append(f"{value} cm/s is not an airflow value in the evidence rows")

    # 4. A bare count is only allowed as "129 BASS-II tests" (the full
    #    dataset count, derived from the data — never the sample size).
    for value in COUNT_RE.findall(sentence or ""):
        if int(value) != stats["total_tests"]:
            unverified.append(f"{value} BASS-II tests is not the dataset count ({stats['total_tests']})")

    # 5. A bare "N tests" count (e.g. "14 tests at the highest oxygen")
    #    is only allowed when N was derived from the data for this answer.
    allowed_counts = {float(n) for n in (extra_allowed or set())}
    for value in re.findall(r"(\d+)\s+tests\b", sentence or ""):
        if float(value) not in allowed_counts and int(value) != stats["total_tests"]:
            unverified.append(f"{value} tests is not a count derived from the data for this answer")

    return {"ok": not unverified, "unverified": sorted(set(unverified))}
