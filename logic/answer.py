# Written with SI assistance (Muse), reviewed by Paridhi Singh
"""Lane B answer builder — one answer, in the format the team agreed:

    VERDICT: INSIDE / NEAR / BEYOND what NASA tested
    One-sentence answer in plain words.
    Closest evidence (up to 3 rows): test ID + material + O2 + airflow + outcome.
    What's not known: the gap, stated plainly.
    Sources: links, kept small.
    Gravity note: every answer says the tests were in microgravity.

v5 changes (PR #1 review, Daksh):
- Min oxygen and min/max airflow now exist alongside max oxygen:
  min_oxygen() (13.6%, test O12), min_airflow() (0.0 cm/s, test O2)
  and max_airflow() (49.0 cm/s, tests O5b and O13a) over the full
  129 rows, all ties returned, number-checked. Airflow uses
  flow_start (first number in Air display); flow_end can run higher
  (P14 ends at 85 cm/s) and is noted, not used for the max.
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


def min_oxygen(rows):
    """The lowest oxygen tested, over the rows given, with ALL ties.
    Full 129 rows: 13.6%, test O12 only."""
    best = None
    for row in rows:
        try:
            value = float(row["oxygen_pct"])
        except (KeyError, TypeError, ValueError):
            continue
        if best is None or value < best:
            best = value
    if best is None:
        return {"min_oxygen": None, "test_ids": [], "materials": []}
    ties = [r for r in rows if r.get("oxygen_pct") not in (None, "") and float(r["oxygen_pct"]) == best]
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


def min_airflow(rows):
    """The lowest airflow tested (flow_start), over the rows given,
    with ALL ties. Full 129 rows: 0.0 cm/s, test O2 only."""
    best = None
    for row in rows:
        value = _airflow_value(row)
        if value is None:
            continue
        if best is None or value < best:
            best = value
    if best is None:
        return {"min_airflow": None, "test_ids": [], "materials": []}
    ties = [r for r in rows if _airflow_value(r) == best]
    return {
        "min_airflow": best,
        "test_ids": [r["test_id"] for r in ties],
        "materials": sorted({r["material"] for r in ties}),
    }


def max_airflow(rows):
    """The highest airflow tested (flow_start), over the rows given,
    with ALL ties. Full 129 rows: 49.0 cm/s, tests O5b and O13a.
    flow_end can run higher (P14 ends at 85 cm/s) — that is a ramp
    inside one test, not the starting airflow, so it is not the max."""
    best = None
    for row in rows:
        value = _airflow_value(row)
        if value is None:
            continue
        if best is None or value > best:
            best = value
    if best is None:
        return {"max_airflow": None, "test_ids": [], "materials": []}
    ties = [r for r in rows if _airflow_value(r) == best]
    return {
        "max_airflow": best,
        "test_ids": [r["test_id"] for r in ties],
        "materials": sorted({r["material"] for r in ties}),
    }


def _extreme_answer(question, label, value, ties, rows, stats):
    """One number-checked answer for a highest/lowest question."""
    if value is None:
        return {
            "question": question,
            "verdict": "NEED_OXYGEN",
            "sentence": "No values for that are in the rows I was given.",
            "evidence": [],
            "nearest_evidence": None,
            "unknown": ["oxygen_pct"],
            "gravity_note": GRAVITY_NOTE,
            "sources": [PSI_25_URL],
            "number_check": {"ok": True, "unverified": []},
        }
    n = len(ties["test_ids"])
    tests = ", ".join(ties["test_ids"])
    sentence = (
        f"The {label} is {value}{'%' if 'oxygen' in label else ' cm/s'}, in {n} "
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
        "unknown": [],
        "gravity_note": GRAVITY_NOTE,
        "sources": [PSI_25_URL],
        "number_check": check,
    }


def answer_lowest_oxygen(rows, stats=None):
    """Answer 'lowest oxygen tested?' with code, all ties."""
    result = min_oxygen(rows)
    return _extreme_answer(
        "What is the lowest oxygen tested?", "lowest oxygen tested",
        result["min_oxygen"], result, rows, stats)


def answer_lowest_airflow(rows, stats=None):
    """Answer 'lowest airflow tested?' with code, all ties."""
    result = min_airflow(rows)
    return _extreme_answer(
        "What is the lowest airflow tested?", "lowest airflow tested",
        result["min_airflow"], result, rows, stats)


def answer_highest_airflow(rows, stats=None):
    """Answer 'highest airflow tested?' with code, all ties."""
    result = max_airflow(rows)
    return _extreme_answer(
        "What is the highest airflow tested?", "highest airflow tested",
        result["max_airflow"], result, rows, stats)


def _material_rows(rows, material):
    """Rows for one material. "PMMA" also matches "PMMA / other"
    (the full-data grouping); other names match exactly."""
    if not material:
        return rows
    return [r for r in rows
            if r.get("material") == material
            or (material == "PMMA" and r.get("material") == "PMMA / other")]


def build_airflow_answer(question, airflow_cm_s, rows, stats=None):
    """Answer an airflow-only question ("Is 10 cm/s inside our
    data?"). Verdict from the BASS-II airflow band in the report
    (0–55 cm/s INSIDE, 55–65 NEAR, above BEYOND); the sentence quotes
    the dataset's observed flow range (0–49 cm/s flow_start)."""
    stats = stats or {"total_tests": len(rows), "o2_min": 13.6, "o2_max": 22.2, "rows_above_21": 0}
    flows = [f for f in (_airflow_value(r) for r in rows) if f is not None]
    low, high = (min(flows), max(flows)) if flows else (0.0, 0.0)
    if airflow_cm_s <= 55:
        verdict, word = "INSIDE", "inside"
    elif airflow_cm_s <= 65:
        verdict, word = "NEAR", "just outside"
    else:
        verdict, word = "BEYOND", "beyond"
    sentence = (
        f"{airflow_cm_s} cm/s airflow is {word} the tested range "
        f"(airflow in the 129 tests runs {low}–{high} cm/s, and the "
        f"BASS-II duct goes to about 55 cm/s), so the rows below are "
        f"{'direct evidence' if verdict == 'INSIDE' else 'the closest evidence we have'}."
    )
    evidence = sorted(rows, key=lambda r: abs((_airflow_value(r) if _airflow_value(r) is not None else float("inf")) - airflow_cm_s))[:3]
    evidence_out = [{
        "test_id": r.get("test_id"), "material": r.get("material"),
        "material_form": r.get("material_form"), "oxygen_pct": r.get("oxygen_pct"),
        "airflow_cm_s": r.get("airflow_cm_s") or None,
        "airflow_end_cm_s": r.get("airflow_end_cm_s") or None,
        "outcome": r.get("outcome") or None, "source": r.get("source"),
        "source_url": r.get("source_url"),
    } for r in evidence]
    check = check_answer_numbers(sentence, evidence_out, stats)
    return {
        "question": question, "verdict": verdict, "sentence": sentence,
        "evidence": evidence_out, "nearest_evidence": None,
        "unknown": ["outcome (not in the PSI-25 CSV — only in the BASS-II report Appendix A)"],
        "gravity_note": GRAVITY_NOTE, "sources": [PSI_25_URL],
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
    high = bool(words & {"highest", "maximum", "most", "higher", "greater"})
    low = bool(words & {"lowest", "minimum", "least", "lower", "smaller"})
    about_oxygen = "oxygen" in words
    about_flow = "airflow" in words or "flow" in words

    if high and about_oxygen:
        return {"path": "code", "answer": answer_highest_oxygen(pool, stats=stats),
                "retrieval": None, "reason": routing["reason"]}
    if low and about_oxygen:
        return {"path": "code", "answer": answer_lowest_oxygen(pool, stats=stats),
                "retrieval": None, "reason": routing["reason"]}
    if high and about_flow:
        return {"path": "code", "answer": answer_highest_airflow(pool, stats=stats),
                "retrieval": None, "reason": routing["reason"]}
    if low and about_flow:
        return {"path": "code", "answer": answer_lowest_airflow(pool, stats=stats),
                "retrieval": None, "reason": routing["reason"]}

    pct = re.search(r"(\d+(?:\.\d+)?)\s*%", q)
    if pct:
        # pool is already filtered to the named material, so pass
        # material=None here: build_answer's own filter matches the
        # sample's "PMMA" but not the full data's "PMMA / other".
        return {"path": "code",
                "answer": build_answer(question, float(pct.group(1)), pool,
                                       material=None, stats=stats),
                "retrieval": None, "reason": routing["reason"]}
    flow = re.search(r"(\d+(?:\.\d+)?)\s*cm/s", q)
    if flow:
        return {"path": "code",
                "answer": build_airflow_answer(question, float(flow.group(1)), rows, stats=stats),
                "retrieval": None, "reason": routing["reason"]}
    return {"path": "code",
            "answer": build_answer(question, None, rows, material=material, stats=stats),
            "retrieval": None, "reason": routing["reason"]}


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

    # Highest/lowest questions: computed over the full 129 rows, not the sample.
    if os.path.exists(full_csv):
        from cards import rows_from_full_csv
        full_rows = rows_from_full_csv(full_csv)
    else:
        full_rows = rows
    print(answer_highest_oxygen(full_rows, stats=stats))
    print()

    # ask(): the website's single call — route + answer.
    for q in [
        "Is 30% oxygen inside our data for PMMA?",
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
