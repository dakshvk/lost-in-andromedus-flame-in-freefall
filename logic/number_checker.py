# Written with SI assistance (Claude), reviewed by Paridhi Singh
"""Lane B number checker — every number in an answer must appear in the
frozen dataset (or in the question itself), or it is flagged UNVERIFIED.

The checker never fixes an answer silently. It returns the list of
unverified numbers so the answer builder can flag them in the open.
"""

import re

NUMBER_RE = re.compile(r"\d+(?:\.\d+)?")
# Test IDs like B1, T25, F2, P22a, T28a are identifiers, not quantities —
# strip them before looking for numbers, or "B1" would flag "1" as unverified.
TEST_ID_RE = re.compile(r"\b[A-Za-z]+\d+[a-z]?\b")


def numbers_in(text):
    """All numbers appearing in a string, as floats (test IDs excluded)."""
    cleaned = TEST_ID_RE.sub(" ", text or "")
    return [float(n) for n in NUMBER_RE.findall(cleaned)]


def check_numbers(text, allowed_numbers, question_numbers=None):
    """Check every number in `text` against the allowed set.

    allowed_numbers: numbers that appear in the frozen dataset
        (e.g. O2 values from the rows, counts like 129, 18).
    question_numbers: numbers that appear in the user's question
        itself (e.g. 30% in "a Moon base at 30% O2") — these are
        the condition being asked about, not a claimed fact.
    Returns {"ok": bool, "unverified": [float, ...]}.
    """
    allowed = {float(n) for n in allowed_numbers}
    if question_numbers:
        allowed |= {float(n) for n in question_numbers}
    found = numbers_in(text)
    unverified = sorted({n for n in found if n not in allowed})
    return {"ok": not unverified, "unverified": unverified}


def allowed_numbers_from_rows(rows):
    """Build the allowed-number set from frozen dataset rows.

    rows: list of dicts with at least `oxygen_pct` (and optionally
    `airflow_cm_s`). Blank values are skipped, never guessed.
    """
    allowed = set()
    for row in rows:
        for key in ("oxygen_pct", "airflow_cm_s"):
            value = row.get(key)
            if value not in (None, ""):
                allowed.add(float(value))
    allowed.add(float(len(rows)))  # the row count itself, e.g. 6 in the sample
    return allowed
