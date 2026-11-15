# Written with SI assistance (Muse), reviewed by Paridhi Singh
"""Lane B answer builder — one answer, in the format the team agreed:

    VERDICT: INSIDE / NEAR / BEYOND what NASA tested
    One-sentence answer in plain words.
    Closest evidence (up to 3 rows): test ID + material + O2 + airflow + outcome.
    What's not known: the gap, stated plainly.
    Sources: links, kept small.
    Gravity note: every answer says the tests were in microgravity.

v9 changes (PR #1 review, Daksh, Nov 14):
- ask() now forwards the airflow in a % question to build_answer:
  "PMMA at 20% oxygen and 45 cm/s airflow?" used to drop the
  45 cm/s entirely, so it came back INSIDE on oxygen alone. The
  per-material flow range in classify() (v9) now sees it: BEYOND.
- closest_rows() ranks by oxygen AND flow when an airflow is given
  (doc Step 1): each distance is scaled by its range in the pool,
  and the two are added. A test whose flow changed covers its whole
  span, so a target flow inside that span is distance 0 for that row.
- The INSIDE sentence quotes the material's own test count, without
  Link rows (Link rows are paper rod data, always burning, and the
  README says they don't count as outcomes): PMMA is 102, not 200.
- answer_lowest_airflow() adds a note when every test at the lowest
  airflow carries Lane A's low-flow flag: low readings are uncertain.
- gravity_note() is now a function of the rows: the pressure range
  comes from the data (the recorded pressure_kPa values,
  70.7–100.0 kPa), not fixed text.
- build_airflow_answer() takes a material: with one, the verdict
  uses that material's own flow range with the 25% margin; without
  one, the BASS-II hardware band (0–55 cm/s) as before.

v7 changes (Lane A swap, Nov 14):
- Lane B now reads Lane A's data/tests.json (200 rows) when it sits
  next to the repo: dataset_stats_tests_json() (total 200, O2
  13.6–22.2% at standard pressure, 32 rows above 21%), and the
  highest/lowest answers run over those rows. The PSI-25 CSV is the
  fallback; the 6-row sample is the last resort.
- Sentences say "NASA's tests" and "200 tests", not "BASS-II tests":
  the dataset now spans BASS-II, Saffire I–III, Saffire IV/V and
  Link et al. 2018.
- Highest/lowest oxygen and airflow exclude the low-pressure
  Saffire V rows (~71 kPa): the highest oxygen tested is 22.2%
  (14 tests), not 26.2%. Those rows stay labeled by pressure and
  are cited separately as nearest evidence for Moon-cabin questions.
- build_airflow_answer quotes stats["total_tests"] instead of a
  hard-coded 129, and its outcome unknown is conditional now.
- "in 1 tests" fixed in answer_highest_oxygen.

v6 changes (PR #1 review, Daksh, Nov 14):
- Airflow parser fixed: the Air display column mixes transducer
  readings (cm/s) with fan-pot settings (~0.3–2.7, after "pot" or
  in parentheses: P14 ".85", P3b "0.85", P15 "0.36") and fan
  readings (40–62: O5a "(49, 62, 49, 44, 42)", O5b "49", O13a
  "49, 44, 42, ..."). The old parser took the first number, so
  "highest airflow 49 cm/s (O5b, O13a)" and "P14 ends at 85 cm/s"
  were pot/fan readings, not flows. cards._parse_air_display now
  cuts at "pot", drops pot-sized parenthesised groups, and drops
  numbers above the restrictor cap (35 cm/s with two restrictors,
  55 otherwise). O5b's real flow is 5 cm/s (report: "Fan pot 1.3
  (5 cm/s)"); O13a's real flows are (5, 2, 0).
- Min/max airflow now use the lower of start/end (lowest) and the
  higher of start/end (highest) per test, not start only: T25 and
  T26 dropped to 2.5 cm/s during the test. Lowest-airflow answers
  name the material ("for SIBAL"). Lowest oxygen (13.6%, O12)
  notes that O12 never ignited (PSI-25 CSV Air display: "no ign
  at any flow").
- classify() now returns INVALID for oxygen outside 0–100%, and
  BEYOND for a material with fewer than 3 rows on a real dataset
  (20+ rows) — the "fewer than 3 rows means extrapolated" rule;
  it does not apply to the 6-row sample.
- ask(question, rows, stats=None) is the website's single call: it
  routes with rag.route() and returns the answer — code answers from
  classify()/max/min functions, RAG answers from retrieve().
  A material named in the question filters the code answers
  (e.g. "highest oxygen for SIBAL", "lowest airflow for SIBAL").
- Saffire V nearest evidence: corrected citation — the numbers come
  from the ICES 2021 Saffire IV/V paper, Table 1 (NTRS 20210011521):
  V-2 cotton 26.2% O2 at 70.7 kPa, V-3 PMMA 25.4% at 71.3 kPa,
  V-4 PMMA 25.7% at 72.6 kPa, all at 20 cm/s flow. Ranges used:
  25.4–26.2% O2, 70.7–72.6 kPa. Moon cabin from the challenge notes:
  30%+ O2 at 10.2 psi or less. "per Daksh" removed; Saffire IV/V
  data is described as "not in the PSI tables we loaded".
"""

import csv
import re

from classifier import (
    classify, dataset_range, material_ranges, _same_material,
    AIRFLOW_MAX, flow_range, FLOW_MARGIN,
)
from number_checker import allowed_numbers_from_rows, check_answer_numbers

PSI_25_URL = "https://psi.nasa.gov/physci/repo/data/investigations/PSI-25"
GRAVITY_NOTE = (
    "These tests were in microgravity on the ISS. The Moon is about "
    "one-sixth Earth's gravity, and pressure differs, so a Moon-base "
    "condition is not covered by these tests."
)


def gravity_note(rows=None):
    """The gravity note. The pressure range comes from the data (the
    recorded pressure_kPa values), not fixed text — most rows are at
    standard cabin pressure and record no value, so the range is the
    recorded Saffire IV/V pressures (70.7–100.0 kPa). With no rows,
    or no recorded pressures, the base text is used."""
    if not rows:
        return GRAVITY_NOTE
    pressures = [float(r["pressure_kPa"]) for r in rows
                 if r.get("pressure_kPa") is not None]
    if not pressures:
        return GRAVITY_NOTE
    return (
        "These tests were in microgravity on the ISS. The Moon is about "
        "one-sixth Earth's gravity. Pressures recorded in the data run "
        f"{min(pressures)}–{max(pressures)} kPa, so a Moon-base condition "
        "is not covered by these tests."
    )


def load_rows(path):
    """Load the frozen sample/full dataset. Blank = unknown, never guessed."""
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def dataset_stats_tests_json(path):
    """Derive the dataset stats from Lane A's data/tests.json (200 rows).

    Returns {"total_tests", "o2_min", "o2_max", "rows_above_21"}.
    o2_min/o2_max and rows_above_21 are computed over standard-pressure
    rows only: the three Saffire V rows at 70.7–72.6 kPa stay labeled
    by pressure and never join the normal ranges (open team decision).
    The two context-only PSI-100 rows have no O2 and are skipped for
    the range, but they count in total_tests (they are rows in the file).
    Read the real file — do not type these numbers in.
    """
    import json

    with open(path, encoding="utf-8") as f:
        tests = json.load(f)
    o2 = []
    for t in tests:
        pressure = t.get("pressure_kPa")
        if pressure is not None and pressure < 90.0:
            continue
        value = t.get("o2_start")
        if value is not None:
            o2.append(float(value))
    return {
        "total_tests": len(tests),
        "o2_min": min(o2),
        "o2_max": max(o2),
        "rows_above_21": sum(1 for v in o2 if v > 21.0),
    }


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


def _standard_pressure(row):
    """True unless the row is a low-pressure Saffire V row (~71 kPa):
    those stay labeled by pressure and never join the normal extremes,
    ranges, or the evidence pool (open team decision, Nov 14). Rows
    from the PSI CSV or the sample carry no pressure_kPa and count as
    standard pressure."""
    pressure = row.get("pressure_kPa")
    return pressure is None or pressure >= 90.0


def max_oxygen(rows):
    """The highest oxygen tested, over the standard-pressure rows
    given, with ALL ties.

    Returns {"max_oxygen": float, "test_ids": [...], "materials": [...]}.
    Use the full dataset, not the 6-row sample: the sample's max is
    also 22.2%, but it only shows 3 of the 14 tests at that level.
    The Saffire V rows (25.4–26.2% at ~71 kPa) are NOT counted here —
    they stay labeled by pressure, and the nearest-evidence field
    cites them separately for Moon-cabin questions.
    """
    best = None
    for row in rows:
        if not _standard_pressure(row):
            continue
        try:
            value = float(row["oxygen_pct"])
        except (KeyError, TypeError, ValueError):
            continue
        if best is None or value > best:
            best = value
    if best is None:
        return {"max_oxygen": None, "test_ids": [], "materials": []}
    ties = [r for r in rows if _standard_pressure(r) and r.get("oxygen_pct") not in (None, "") and float(r["oxygen_pct"]) == best]
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
            "gravity_note": gravity_note(rows),
            "sources": [PSI_25_URL],
            "number_check": {"ok": True, "unverified": []},
        }
    n = len(result["test_ids"])
    tests = ", ".join(result["test_ids"])
    sentence = (
        f"The highest oxygen tested is {result['max_oxygen']}%, in {n} "
        f"test{'s' if n != 1 else ''} "
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
        "gravity_note": gravity_note(rows),
        "sources": [PSI_25_URL],
        "number_check": check,
    }


def min_oxygen(rows):
    """The lowest oxygen tested, over the standard-pressure rows
    given, with ALL ties. Full dataset: 13.6%, test O12 only."""
    best = None
    for row in rows:
        if not _standard_pressure(row):
            continue
        try:
            value = float(row["oxygen_pct"])
        except (KeyError, TypeError, ValueError):
            continue
        if best is None or value < best:
            best = value
    if best is None:
        return {"min_oxygen": None, "test_ids": [], "materials": []}
    ties = [r for r in rows if _standard_pressure(r) and r.get("oxygen_pct") not in (None, "") and float(r["oxygen_pct"]) == best]
    return {
        "min_oxygen": best,
        "test_ids": [r["test_id"] for r in ties],
        "materials": sorted({r["material"] for r in ties}),
    }


def _airflow_value(row):
    """flow_start as a float, or None when the row has no numeric airflow."""
    try:
        return float(row["airflow_cm_s"])
    except (KeyError, TypeError, ValueError):
        return None


def _airflow_end(row):
    """flow_end as a float, or None when the row has no second flow."""
    try:
        return float(row["airflow_end_cm_s"])
    except (KeyError, TypeError, ValueError):
        return None


def _flow_low(row):
    """The lowest airflow a test actually saw: the lower of
    flow_start and flow_end. T25 and T26 dropped to 2.5 cm/s during
    the test, so their lowest is 2.5, not the 5.0 they started at."""
    values = [v for v in (_airflow_value(row), _airflow_end(row)) if v is not None]
    return min(values) if values else None


def _flow_high(row):
    """The highest airflow a test actually saw: the higher of
    flow_start and flow_end."""
    values = [v for v in (_airflow_value(row), _airflow_end(row)) if v is not None]
    return max(values) if values else None


def min_airflow(rows):
    """The lowest airflow tested (lower of start/end per test), over
    the standard-pressure rows given, with ALL ties. Rows with no flow
    number at all (O12) are skipped."""
    best = None
    for row in rows:
        if not _standard_pressure(row):
            continue
        value = _flow_low(row)
        if value is None:
            continue
        if best is None or value < best:
            best = value
    if best is None:
        return {"min_airflow": None, "test_ids": [], "materials": []}
    ties = [r for r in rows if _standard_pressure(r) and _flow_low(r) == best]
    return {
        "min_airflow": best,
        "test_ids": [r["test_id"] for r in ties],
        "materials": sorted({r["material"] for r in ties}),
    }


def max_airflow(rows):
    """The highest airflow tested (higher of start/end per test),
    over the standard-pressure rows given, with ALL ties. After the
    parser fix (v6), pot settings and fan readings are no longer
    stored as airflow, so the old 49.0 cm/s (O5b, O13a) is gone."""
    best = None
    for row in rows:
        if not _standard_pressure(row):
            continue
        value = _flow_high(row)
        if value is None:
            continue
        if best is None or value > best:
            best = value
    if best is None:
        return {"max_airflow": None, "test_ids": [], "materials": []}
    ties = [r for r in rows if _standard_pressure(r) and _flow_high(r) == best]
    return {
        "max_airflow": best,
        "test_ids": [r["test_id"] for r in ties],
        "materials": sorted({r["material"] for r in ties}),
    }


def _extreme_answer(question, label, value, ties, rows, stats, material=None, note=None):
    """One number-checked answer for a highest/lowest question.
    When a material is named, the sentence says so ("lowest airflow
    tested for SIBAL"). A note (e.g. O12 never ignited) is returned
    as its own field, not folded into the sentence."""
    if value is None:
        return {
            "question": question,
            "verdict": "NEED_OXYGEN",
            "sentence": "No values for that are in the rows I was given.",
            "evidence": [],
            "nearest_evidence": None,
            "note": note,
            "unknown": ["oxygen_pct"],
            "gravity_note": gravity_note(rows),
            "sources": [PSI_25_URL],
            "number_check": {"ok": True, "unverified": []},
        }
    n = len(ties["test_ids"])
    tests = ", ".join(ties["test_ids"])
    for_material = f" for {material}" if material else ""
    sentence = (
        f"The {label}{for_material} is {value}{'%' if 'oxygen' in label else ' cm/s'}, in {n} "
        f"test{'s' if n != 1 else ''} ({tests}) — materials: "
        f"{', '.join(ties['materials'])}."
    )
    evidence = [r for r in rows if r.get("test_id") in ties["test_ids"]]
    stats = stats or {"total_tests": len(rows), "o2_min": 13.6, "o2_max": 22.2, "rows_above_21": 0}
    check = check_answer_numbers(sentence, evidence, stats, extra_allowed={float(n)})
    return {
        "question": question,
        "verdict": "INSIDE",
        "sentence": sentence,
        "evidence": evidence,
        "nearest_evidence": None,
        "note": note,
        "unknown": [],
        "gravity_note": gravity_note(rows),
        "sources": [PSI_25_URL],
        "number_check": check,
    }


def answer_lowest_oxygen(rows, stats=None, material=None):
    """Answer 'lowest oxygen tested?' with code, all ties. When the
    lowest test is O12 (13.6%), note that O12 never ignited — the
    PSI-25 CSV's Air display for O12 reads 'no ign at any flow'."""
    result = min_oxygen(rows)
    note = None
    if "O12" in result["test_ids"]:
        note = ("O12, the lowest-oxygen test at 13.6%, never ignited — "
                "the PSI-25 CSV's Air display for O12 reads "
                "'no ign at any flow'.")
    return _extreme_answer(
        "What is the lowest oxygen tested?", "lowest oxygen tested",
        result["min_oxygen"], result, rows, stats,
        material=material, note=note)


def answer_lowest_airflow(rows, stats=None, material=None):
    """Answer 'lowest airflow tested?' with code, all ties. When every
    test at the lowest airflow carries Lane A's low-flow flag, the
    note says low readings are uncertain (the report says low flows
    have high error bars; the team's cutoff is 2 cm/s)."""
    result = min_airflow(rows)
    note = None
    ties = [r for r in rows if r.get("test_id") in result["test_ids"]]
    if ties and all(r.get("low_flow_uncertain") for r in ties):
        note = (
            "All tests at the lowest airflow carry the low-flow flag — "
            "low readings are uncertain (flows below 2 cm/s have high "
            "error bars), so this is a low reading, not an exact flow."
        )
    return _extreme_answer(
        "What is the lowest airflow tested?", "lowest airflow tested",
        result["min_airflow"], result, rows, stats, material=material,
        note=note)


def answer_highest_airflow(rows, stats=None, material=None):
    """Answer 'highest airflow tested?' with code, all ties."""
    result = max_airflow(rows)
    return _extreme_answer(
        "What is the highest airflow tested?", "highest airflow tested",
        result["max_airflow"], result, rows, stats, material=material)


def _material_rows(rows, material):
    """Rows for one material. "PMMA" also matches "PMMA / other"
    (the full-data grouping); other names match exactly."""
    if not material:
        return rows
    return [r for r in rows
            if r.get("material") == material
            or (material == "PMMA" and r.get("material") == "PMMA / other")]


def build_airflow_answer(question, airflow_cm_s, rows, stats=None, material=None):
    """Answer an airflow-only question ("Is 10 cm/s inside our
    data?"). Verdict from the BASS-II airflow band in the report
    (0–55 cm/s INSIDE, 55–65 NEAR, above BEYOND) — or, when a material
    is given, from that material's own tested flow range with the 25%
    margin (doc Step 1 items 3 and 4). The sentence quotes the
    observed flow range (low/high across start and end flows)."""
    # The gravity note's pressure range comes from the data BEFORE
    # the standard-pressure filter below (as in build_answer).
    note = gravity_note(rows)
    # Same pressure filter as build_answer: the low-pressure Saffire
    # V rows never join the evidence pool or the observed flow range.
    rows = [r for r in rows if _standard_pressure(r)]
    stats = stats or {"total_tests": len(rows), "o2_min": 13.6, "o2_max": 22.2, "rows_above_21": 0}
    pool = _material_rows(rows, material) if material else rows
    lows = [f for f in (_flow_low(r) for r in pool) if f is not None]
    highs = [f for f in (_flow_high(r) for r in pool) if f is not None]
    low, high = (min(lows), max(highs)) if lows and highs else (0.0, 0.0)
    # The count is for this material, without Link rows (as in
    # build_answer) — or the whole dataset when no material is given.
    count = (sum(1 for r in pool if "link" not in (r.get("source") or "").lower())
             if material else stats["total_tests"])
    if material and lows and highs:
        # The material's own range with the 25% margin.
        margin = FLOW_MARGIN * (high - low)
        near_low = max(0.0, low - margin)
        near_high = high + margin
        if low <= airflow_cm_s <= high:
            verdict, word = "INSIDE", "inside"
        elif near_low <= airflow_cm_s <= near_high:
            verdict, word = "NEAR", "just outside"
        else:
            verdict, word = "BEYOND", "beyond"
        range_text = f"{material} airflow runs {low}–{high} cm/s in {count} tests"
    else:
        if airflow_cm_s <= 55:
            verdict, word = "INSIDE", "inside"
        elif airflow_cm_s <= 65:
            verdict, word = "NEAR", "just outside"
        else:
            verdict, word = "BEYOND", "beyond"
        range_text = (f"airflow in the {stats['total_tests']} tests runs "
                      f"{low}–{high} cm/s, and the BASS-II duct goes to "
                      "about 55 cm/s")
    sentence = (
        f"{airflow_cm_s} cm/s airflow is {word} the tested range "
        f"({range_text}), so the rows below are "
        f"{'direct evidence' if verdict == 'INSIDE' else 'the closest evidence we have'}."
    )
    evidence = sorted(pool, key=lambda r: abs((_airflow_value(r) if _airflow_value(r) is not None else float("inf")) - airflow_cm_s))[:3]
    evidence_out = [{
        "test_id": r.get("test_id"), "material": r.get("material"),
        "material_form": r.get("material_form"), "oxygen_pct": r.get("oxygen_pct"),
        "airflow_cm_s": r.get("airflow_cm_s") or None,
        "airflow_end_cm_s": r.get("airflow_end_cm_s") or None,
        "outcome": r.get("outcome") or None, "source": r.get("source"),
        "source_url": r.get("source_url"),
    } for r in evidence]
    check = check_answer_numbers(sentence, evidence_out, stats,
                                 flow_bounds=(low, high),
                                 question_flow=airflow_cm_s,
                                 extra_flows={AIRFLOW_MAX},
                                 extra_allowed={float(count)})
    unknown = []
    if any(not r.get("outcome") for r in evidence):
        unknown.append("outcome (not recorded for some evidence rows — not guessed)")
    return {
        "question": question, "verdict": verdict, "sentence": sentence,
        "evidence": evidence_out, "nearest_evidence": None,
        "unknown": unknown,
        "gravity_note": note, "sources": [PSI_25_URL],
        "number_check": check,
    }


def ask(question, rows, stats=None):
    """The website's single call: route the question and return the answer.

    Returns {"path": "code"|"rag", "answer": dict|None,
    "retrieval": dict|None, "reason": str}. Code answers come from
    classify()/max/min functions; RAG answers from retrieve().
    A material named in the question filters the code answers.
    """
    import re
    from rag import route, retrieve, _named_material

    routing = route(question)
    if routing["path"] == "rag":
        return {"path": "rag", "answer": None,
                "retrieval": retrieve(question, rows), "reason": routing["reason"]}

    q = (question or "").lower()
    words = set(re.findall(r"[a-z]+", q))
    material = _named_material(question)
    pool = _material_rows(rows, material)
    # The gravity note's pressure range comes from the FULL dataset,
    # not the material pool: the pool for a PMMA question holds only
    # 100.0 kPa (Saffire IV), so a note computed from it would read
    # "100.0–100.0 kPa" and hide the Saffire V low-pressure tests
    # (70.7–72.6 kPa). The builders compute their own note from the
    # pool; this overrides it with the dataset-wide one.
    note = gravity_note(rows)

    def code_result(answer):
        if answer is not None:
            answer["gravity_note"] = note
        return {"path": "code", "answer": answer,
                "retrieval": None, "reason": routing["reason"]}

    high = bool(words & {"highest", "maximum", "most", "higher", "greater"})
    low = bool(words & {"lowest", "minimum", "least", "lower", "smaller"})
    about_oxygen = "oxygen" in words
    about_flow = "airflow" in words or "flow" in words

    if high and about_oxygen:
        return code_result(answer_highest_oxygen(pool, stats=stats))
    if low and about_oxygen:
        return code_result(answer_lowest_oxygen(pool, stats=stats, material=material))
    if high and about_flow:
        return code_result(answer_highest_airflow(pool, stats=stats, material=material))
    if low and about_flow:
        return code_result(answer_lowest_airflow(pool, stats=stats, material=material))

    pct = re.search(r"(\d+(?:\.\d+)?)\s*%", q)
    flow = re.search(r"(\d+(?:\.\d+)?)\s*cm/s", q)
    if pct:
        # Pass the material through: build_answer's classify matches
        # "PMMA" against the full data's "PMMA / other" via
        # _same_material, and closest_rows falls back to the
        # pre-filtered pool when its exact match fails. Passing
        # material=None here used to make the sentence quote the
        # overall range while the verdict used the material's range
        # (e.g. 14% for Wax: BEYOND, but the sentence said the tests
        # cover 13.6–22.2% — self-contradictory). The airflow is
        # forwarded too: a question like "PMMA at 20% and 45 cm/s"
        # used to drop the 45 cm/s entirely, so it came back INSIDE
        # on oxygen alone — the per-material flow range never saw it.
        return code_result(build_answer(question, float(pct.group(1)), pool,
                                        airflow_cm_s=(float(flow.group(1)) if flow else None),
                                        material=material, stats=stats))
    if flow:
        return code_result(build_airflow_answer(question, float(flow.group(1)), rows,
                                                stats=stats, material=material))
    return code_result(build_answer(question, None, rows, material=material, stats=stats))


def _is_outcome_question(question):
    """True when the question asks about an outcome (burned, ignited,
    extinguished, how long a flame lasted). Outcomes come only from
    the BASS-II report Appendix A — never from Link et al. rows,
    which are rod data from the paper, not BASS-II tests."""
    words = set(re.findall(r"[a-z]+", (question or "").lower()))
    return bool(words & {
        "outcome", "outcomes", "burn", "burned", "burning", "ignite",
        "ignited", "ignition", "extinguish", "extinguished", "flame",
        "spread", "last", "lasted",
    })


def rows_for_outcome_question(rows, question):
    """Evidence pool for an outcome question: Link et al. rows are
    never in it. For any other question the rows pass through
    unchanged."""
    if not _is_outcome_question(question):
        return rows
    return [r for r in rows if "link" not in (r.get("source") or "").lower()]


def closest_rows(rows, oxygen_pct, limit=3, material=None, airflow_cm_s=None):
    """Up to `limit` rows closest to the question. When an airflow is
    given, rows rank by oxygen AND flow (doc Step 1): each distance is
    scaled by its range in the pool, and the two are added. A test
    whose flow changed covers its whole span, so a target flow inside
    that span is distance 0 for that row. With no airflow, oxygen
    alone decides (as before)."""
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
    if airflow_cm_s is None:
        return sorted(pool, key=lambda r: abs(o2(r) - oxygen_pct))[:limit]

    o2_vals = [o2(r) for r in pool if o2(r) != float("inf")]
    o2_span = (max(o2_vals) - min(o2_vals)) if o2_vals else 0.0
    flow_low, flow_high = flow_range(pool)
    flow_span = (flow_high - flow_low) if flow_low is not None else 0.0

    def score(row):
        total = 0.0
        if o2_span:
            total += abs(o2(row) - oxygen_pct) / o2_span
        if flow_span:
            lo, hi = _flow_low(row), _flow_high(row)
            if lo is None:
                # No flow recorded: this row has no flow evidence, so
                # it ranks below any row with a flow (10 is far above
                # any normalised flow distance in the pool).
                total += 10.0
            elif lo <= airflow_cm_s <= hi:
                pass  # target flow is inside this test's span
            else:
                total += min(abs(airflow_cm_s - lo),
                             abs(airflow_cm_s - hi)) / flow_span
        return total

    return sorted(pool, key=score)[:limit]


def build_answer(question, oxygen_pct, rows, airflow_cm_s=None, material=None, stats=None):
    """Build one guarded answer. Returns a dict the website can render."""
    # The gravity note's pressure range comes from the data BEFORE the
    # standard-pressure filter below: the filter drops the Saffire V
    # rows (70.7–72.6 kPa), leaving only 100.0 kPa, so a note computed
    # after the filter would read "100.0–100.0 kPa".
    note = gravity_note(rows)
    # The low-pressure Saffire V rows (~71 kPa) stay labeled by
    # pressure and never join the normal ranges or the evidence pool.
    # Left in, they stretch the overall oxygen range to 26.2% — so
    # 24% oxygen reads INSIDE even though the quoted range is
    # 13.6–22.2% — and they show up as the closest rows for
    # Moon-cabin questions (the nearest-evidence field already cites
    # them separately). Rows from the PSI CSV or the sample carry no
    # pressure_kPa and count as standard pressure.
    rows = [r for r in rows if _standard_pressure(r)]
    result = classify(oxygen_pct, airflow_cm_s, material=material, rows=rows)
    verdict = result["verdict"]

    if verdict == "NEED_OXYGEN":
        return {
            "question": question,
            "verdict": verdict,
            "sentence": "I need an oxygen value to answer that — what oxygen level are you asking about?",
            "evidence": [],
            "unknown": ["oxygen_pct"],
            "gravity_note": note,
            "sources": [PSI_25_URL],
            "number_check": {"ok": True, "unverified": []},
        }

    if verdict == "INVALID":
        return {
            "question": question,
            "verdict": verdict,
            "sentence": result["reason"],
            "evidence": [],
            "unknown": [],
            "gravity_note": note,
            "sources": [PSI_25_URL],
            "number_check": {"ok": True, "unverified": []},
        }

    evidence = closest_rows(
        rows_for_outcome_question(rows, question), oxygen_pct,
        material=material, airflow_cm_s=airflow_cm_s)
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
    count = total

    # When a material is given, the sentence must quote THAT material's
    # tested range — quoting the overall range would contradict the verdict
    # (e.g. 14% O2 is inside 13.6–22.2% overall, but BEYOND for SIBAL,
    # whose tested range is 16.4–20.8% in the full data).
    if material and rows:
        per_material = material_ranges(rows)
        matched = next((k for k in per_material if _same_material(k, material)), None)
        if matched is not None:
            r_min, r_max = per_material[matched]
            range_text = f"{material} {r_min}–{r_max}% oxygen"
            range_bounds = (r_min, r_max)
            # The count is for THIS material, without Link rows — Link
            # rows are paper rod data, always burning, and the README
            # says they don't count as outcomes (Daksh, Nov 14).
            # PMMA: 102 (154 minus 52 Link), not 200.
            count = sum(1 for r in rows
                        if _same_material(r.get("material"), material)
                        and "link" not in (r.get("source") or "").lower())
        else:
            range_text = f"{o2_min}–{o2_max}% oxygen"
            range_bounds = None
    else:
        range_text = f"{o2_min}–{o2_max}% oxygen"
        range_bounds = None

    # The material's flow range, for the sentence when the verdict is
    # driven by airflow (below): the sentence must name the airflow,
    # not the oxygen, when the oxygen is inside and the airflow is
    # what is outside. Flow bounds go to the number checker too.
    flow_range_text = None
    flow_bounds = None
    if material and rows:
        pool = [r for r in rows if _same_material(r.get("material"), material)]
        flo, fhi = flow_range(pool)
        if flo is not None:
            flow_range_text = f"{material} {flo}–{fhi} cm/s"
            flow_bounds = (flo, fhi)

    drivers = result.get("drivers", [])
    air_driven = "airflow" in drivers
    o2_driven = "oxygen" in drivers
    if verdict == "BEYOND":
        if air_driven and not o2_driven:
            sentence = (
                f"{airflow_cm_s} cm/s airflow is beyond what was tested "
                f"({flow_range_text or 'the BASS-II duct goes to about 55 cm/s'}), so "
                "we can only show the closest tests, not an answer for that condition."
            )
        elif o2_driven and not air_driven:
            sentence = (
                f"NASA's tests cover {range_text}, so "
                f"{oxygen_pct}% oxygen is beyond what was tested — "
                "we can only show the closest tests, not an answer for that condition."
            )
        else:
            sentence = (
                f"{oxygen_pct}% oxygen and {airflow_cm_s} cm/s airflow are both "
                f"beyond what was tested ({range_text}), so we can only show "
                "the closest tests, not an answer for that condition."
            )
    elif verdict == "NEAR":
        if air_driven and not o2_driven:
            sentence = (
                f"{airflow_cm_s} cm/s airflow is just outside the tested range "
                f"({flow_range_text or 'the BASS-II duct goes to about 55 cm/s'}), so "
                "the closest tested rows are the best evidence we have — "
                "treat them as near, not exact."
            )
        elif o2_driven and not air_driven:
            sentence = (
                f"{oxygen_pct}% oxygen is just outside the tested range "
                f"({range_text}), so the closest tested rows are the best "
                "evidence we have — treat them as near, not exact."
            )
        else:
            sentence = (
                f"{oxygen_pct}% oxygen and {airflow_cm_s} cm/s airflow are both "
                f"just outside the tested range ({range_text}), so the closest "
                "tested rows are the best evidence we have — treat them as "
                "near, not exact."
            )
    else:
        sentence = (
            f"{oxygen_pct}% oxygen is inside the tested range "
            f"({range_text}, {count} tests), so the rows below "
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
        unknown.append("dataset stats are from the 6-row sample only — the full dataset (tests.json) was not loaded, so do not quote these as dataset numbers")
    # Only claim airflow is unknown when the evidence rows really lack it.
    if any(not row.get("airflow_cm_s") for row in evidence):
        unknown.append("airflow in cm/s for some evidence rows (no flow value recorded for those rows)")
    if any(not row.get("outcome") for row in evidence):
        unknown.append("outcome (not recorded for some evidence rows — not guessed)")

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
        "gravity_note": note,
        "sources": [PSI_25_URL],
    }

    answer["number_check"] = check_answer_numbers(
        sentence, evidence_out, stats, question_oxygen=oxygen_pct,
        range_bounds=range_bounds, extra_allowed={float(count)},
        question_flow=airflow_cm_s, flow_bounds=flow_bounds,
        extra_flows={AIRFLOW_MAX},
    )
    if not answer["number_check"]["ok"]:
        answer["sentence"] += (
            f" [UNVERIFIED: {answer['number_check']['unverified']}]"
        )
    return answer


if __name__ == "__main__":
    import os

    tests_json = os.path.join(os.path.dirname(__file__), "..", "data", "tests.json")
    full_csv = os.path.join(os.path.dirname(__file__), "..", "data", "raw",
                            "PSI-25_Experimental table_BASS-II.csv")
    # The demo questions use the full dataset — tests.json (200 rows)
    # when it is next to the repo, else the real PSI file, else the
    # 6-row sample (and the note says so). They used to run on the
    # sample while the stats came from tests.json, which quoted the
    # sample's narrower ranges (e.g. SIBAL 18.5–20.8%) next to the
    # full 200-test stats — wrong once the full data is available.
    if os.path.exists(tests_json):
        from cards import rows_from_tests_json
        full_rows = rows_from_tests_json(tests_json)
        stats = dataset_stats_tests_json(tests_json)
    elif os.path.exists(full_csv):
        from cards import rows_from_full_csv
        full_rows = rows_from_full_csv(full_csv)
        stats = dataset_stats(full_csv)
    else:
        full_rows = load_rows("sample_data.csv")
        stats = None
        print("(neither tests.json nor the full PSI CSV was found next to the repo — answers from the 6-row sample)")
    for q, o2, mat in [
        ("A Moon base runs at 30% oxygen. What does NASA's testing cover?", 30.0, None),
        ("What about 20% oxygen?", 20.0, None),
        ("What about 24% oxygen?", 24.0, None),
        ("What about 14% oxygen for SIBAL?", 14.0, "SIBAL"),
        ("What about oxygen with no value given?", None, None),
    ]:
        print(build_answer(q, o2, full_rows, material=mat, stats=stats))
        print()

    # Highest/lowest questions: computed over the same full rows.
    print(answer_highest_oxygen(full_rows, stats=stats))
    print()

    # ask(): the website's single call — route + answer.
    for q in [
        "Is 30% oxygen inside our data for PMMA?",
        "PMMA at 20% oxygen and 45 cm/s airflow?",
        "What is the highest oxygen for SIBAL?",
        "Which SIBAL test had the lowest airflow?",
        "What is the lowest oxygen tested?",
        "What is the highest airflow tested?",
        "How does BASS differ from BASS-II?",
        "What is the same hardware used in these tests?",
        "What about flexible tubing?",
    ]:
        out = ask(q, full_rows, stats=stats)
        print(f"ask({q!r}) -> path={out['path']}")
        if out["answer"] is not None:
            print(" ", out["answer"]["sentence"], "| check:", out["answer"]["number_check"])
        else:
            print("  retrieval:", [(r["entry"]["id"], r["method"]) for r in out["retrieval"]["results"]] if out["retrieval"]["match"] else "no match")
        print()
