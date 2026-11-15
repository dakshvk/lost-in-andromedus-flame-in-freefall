# Written with SI assistance (Muse), reviewed by Paridhi Singh
"""Lane B material cards — one card per material, four lines, no more.

v10 changes (PR #1 review, Daksh, Nov 14):
- rows_from_tests_json() now canonicalises material names: Lane A's
  tests.json records "wax" and "silicone" in lowercase, but the CSV
  path and the question matcher use "Wax" and "Silicone" — without
  this, ask() matched "Wax" against rows that say "wax" and found
  nothing, so "Will wax burn at 17%?" came back INSIDE with an empty
  evidence list.

v9 changes (PR #1 review, Daksh, Nov 14):
- rows_from_tests_json() now takes low_flow_uncertain from Lane A's
  flags instead of computing it: Lane A's check covers both start
  and end flow, so a row that ends at 0 cm/s (O13a, O15a, O15b) is
  flagged even when it starts at 5. The CSV fallback computes it
  from both start and end (same rule, no Lane A flags on that path).
- build_card() outcome counts exclude Link rows: they are paper rod
  data, always burning, and Lane A's README says they don't count as
  outcomes. PMMA is 76 of 102, not 130 of 154.

v7 changes (Lane A swap, Nov 14):
- New rows_from_tests_json(): converts Lane A's data/tests.json
  (200 rows) into Lane B rows. Saffire V rows at 70.7–72.6 kPa stay
  labeled by pressure ("PMMA (Saffire V, 71.3 kPa)") and never join
  the plain PMMA range; Saffire IV rows at 100.0 kPa keep their
  plain material. Saffire I/III S1/S2 collide, so they become
  "98-S1"/"100-S1". Low-flow flag: flow_start below 2 cm/s is the
  team cutoff (Daksh, Nov 14). Spread rates are carried through but
  their unit is unresolved — no spread-rate answers yet.
- Cards now report real outcomes (tests.json has them: PMMA 129 of
  154 known) and name the actual sources instead of always saying
  BASS-II. Rows with no oxygen (the two context-only Saffire III
  rows) no longer crash the card. "15 -> 15 cm/s" is now "15 cm/s".

v4 changes (PR #1 review, Daksh):
- Cards are built from the FULL 129-row PSI-25 CSV, not the 6-row
  sample. The old cards said "2 tests" and "highest oxygen in the
  sample" — both were wrong, and both PMMA and Nomex claimed to be
  the closest evidence for high oxygen. Real counts: PMMA / other 98,
  Nomex 3, SIBAL 27, Wax 1. Both PMMA / other and Nomex reach 22.2%,
  so both cards now say they are TIED at the highest oxygen tested.
- "Highest oxygen in the sample" is gone: it is the highest oxygen
  in the full dataset.
- Outcome is still not known: it is not in the PSI-25 CSV, only in
  the BASS-II report Appendix A, so the card still says so.
- When the full CSV is not next to the repo, the sample is used and
  the card says so — never silently present sample numbers as dataset
  numbers.
"""

import csv
import json
import os
import re
from collections import defaultdict

from answer import load_rows

PSI_25_URL = "https://psi.nasa.gov/physci/repo/data/investigations/PSI-25"


def group_name(fuel_sample_material):
    """Group one PSI 'Fuel Sample Material' into a card group.

    SIBAL and Nomex are named materials; wax is the Japan Wax candle;
    everything else (PMMA films, rods and slabs, plus rods listed
    without a material name) is 'PMMA / other'. These are grouping
    calls for the cards — Jenisha confirms them in the full clean file.
    """
    s = (fuel_sample_material or "").lower()
    if "sibal" in s:
        return "SIBAL"
    if "nomex" in s:
        return "Nomex"
    if "wax" in s:
        return "Wax"
    return "PMMA / other"


def _form_of(fuel_sample_material, group):
    s = (fuel_sample_material or "").lower()
    if group in ("Nomex", "SIBAL"):
        return "cloth"
    if group == "Wax":
        return "candle"
    for form in ("film", "rod", "slab"):
        if form in s:
            return form
    if "spherical" in s:
        return "sphere"
    if "micron" in s:
        return "film"
    if "thick" in s:
        return "slab"
    return "sample"


def _parse_air_display(raw, restrictor):
    """Parse one PSI 'Air display' cell into (flow_start, flow_end).

    The cell mixes three kinds of numbers, and the BASS-II report
    (NASA/TM-20210011385) says which is which:
    - Transducer readings in cm/s — the real flows. Typically small
      integers or .5 steps (5, 10, 2.5, 2, 0, 7, 4, 15, 20).
    - Fan-pot settings, about 0.3–2.7 — they appear after the word
      "pot"/"pots", or in parentheses (P14 ".85", P3b "0.85", P15
      "0.36"). They are NOT airflow and must not be stored as such.
    - Fan readings, 40–62 (O5a "(49, 62, 49, 44, 42)", O5b "49",
      O13a "49, 44, 42, ..."). With two flow restrictors the duct
      caps at about 35 cm/s, with fewer at about 55 cm/s, so any
      number above the cap for that row's restrictor count is a fan
      reading, not a flow.
    Rules, in order: cut at the word "pot"; drop parenthesised groups
    whose numbers are all pot-sized (max <= 2.7); drop numbers above
    the restrictor cap (35 with two restrictors, else 55). What is
    left, in order, is the flow sequence: first is flow_start,
    last is flow_end (the flow at the end of the test — a ramp like
    B10 "5 4 3 2 1" ends at 1, not 4). Returns (None, None) when no
    flow number survives (e.g. O12, "no ign at any flow").
    Numbers written ".85" (no leading zero) are pot settings, not
    85 cm/s, and "<1" is not a reading of 1 cm/s — both are handled
    before any number is read.
    """
    if not raw:
        return (None, None)
    text = raw
    # ".85" is 0.85, not 85: read numbers with an optional leading dot.
    num_re = r"(?:\d+(?:\.\d+)?|\.\d+)"
    # A pot-sized number directly before "pot" is a pot setting
    # ("0.5 pot", "0.4 pot" in B16) — remove it. A flow number before
    # "pots" ("5 pots 0.4 ..." in P4) is a real flow, so it stays and
    # the cut below drops what follows.
    def _drop_pot_setting(match):
        # match.group(0) is e.g. "0.5 pot" or "5 pots": the number is
        # its first word. Pot-sized (<= 2.7) -> remove the pair;
        # a flow number -> keep it, the cut below drops what follows.
        number = float(match.group(0).split()[0])
        return " " if number <= 2.7 else match.group(0)

    text = re.sub(num_re + r"\s*pots?\b", _drop_pot_setting,
                  text, flags=re.IGNORECASE)
    # Cut at any remaining "pot": everything after is pot settings.
    m = re.search(r"pot", text, re.IGNORECASE)
    if m:
        text = text[:m.start()]
    # "<1" is not a reading of 1 cm/s.
    text = re.sub(r"<\s*" + num_re, " ", text)

    def _drop_pot_group(match):
        nums = [float(x) for x in re.findall(num_re, match.group(0))]
        if nums and max(nums) <= 2.7:
            return " "
        return match.group(0)

    text = re.sub(r"\([^)]*\)", _drop_pot_group, text)
    cap = 35.0 if (restrictor or "").strip() == "2" else 55.0
    nums = [float(x) for x in re.findall(num_re, text)]
    flows = [n for n in nums if n <= cap]
    if not flows:
        return (None, None)
    return (flows[0], flows[-1] if len(flows) > 1 else None)


def _flow_str(value):
    """Format a parsed flow for the Lane B row: 5.0 -> "5", 2.5 -> "2.5"."""
    if value is None:
        return ""
    if float(value) == int(float(value)):
        return str(int(float(value)))
    return str(value)


def _form_from_shape(shape):
    """Normalize a tests.json shape (free text, e.g. "black rod,
    1.27 cm diameter" or "flat fabric, 2 cm wide") to a Lane B form:
    rod / film / cloth / slab / sheet / sphere / candle / unknown."""
    text = (shape or "").lower()
    if "rod" in text:
        return "rod"
    if "film" in text:
        return "film"
    if "fabric" in text or "cloth" in text:
        return "cloth"
    if "slab" in text:
        return "slab"
    if "sheet" in text:
        return "sheet"
    if "spherical" in text:
        return "sphere"
    if "candle" in text:
        return "candle"
    return "unknown"


# Display source name + URL per tests.json source value. The Link
# source name keeps "Link" in it: answer.py's outcome filter excludes
# Link rows from outcome evidence by matching "link" in the source.
TESTS_SOURCES = {
    "psi-25": ("PSI-25", "https://psi.nasa.gov/physci/repo/data/investigations/PSI-25"),
    "psi-98": ("PSI-98 (SAFFIRE-I)", "https://psi.nasa.gov/physci/repo/data/investigations/PSI-98"),
    "psi-99": ("PSI-99 (SAFFIRE-II)", "https://psi.nasa.gov/physci/repo/data/investigations/PSI-99"),
    "psi-100": ("PSI-100 (SAFFIRE-III)", "https://psi.nasa.gov/physci/repo/data/investigations/PSI-100"),
    "paper-link2018": ("Link et al. 2018", "https://pmc.ncbi.nlm.nih.gov/articles/PMC5760683/"),
    "paper-saffire45": ("Saffire IV/V (ICES 2021)", "https://ntrs.nasa.gov/citations/20210011521"),
}

# Low-flow cutoff, team decision (Daksh, Nov 14): the BASS-II report
# says low flows have "high error bars" but gives no number, so 2 cm/s
# is the team's call, written in the limits drawer.
LOW_FLOW_CUTOFF_CM_S = 2.0
# Rows below this pressure are NOT at cabin pressure and must not join
# the normal per-material oxygen ranges: the Saffire V rows at
# 70.7–72.6 kPa stay labeled by pressure (open team decision, Nov 14).
STANDARD_PRESSURE_MIN_KPA = 90.0


# Canonical material names. Lane A's tests.json records "wax" and
# "silicone" in lowercase, but the CSV path (group_name) and the
# question matcher (rag.MATERIAL_NAMES) use "Wax" and "Silicone" —
# without this, ask() matched "Wax" against rows that say "wax" and
# found nothing (v10: "Will wax burn at 17%?" came back INSIDE with
# an empty evidence list). "other" is the one Saffire V cotton row
# (V-2, low pressure); it is left as recorded.
MATERIAL_CANONICAL = {"wax": "Wax", "silicone": "Silicone"}


def _canonical_material(material):
    return MATERIAL_CANONICAL.get((material or "").lower(), material or "unknown")


def rows_from_tests_json(path):
    """Convert Lane A's data/tests.json (200 rows) into Lane B rows
    (same schema as sample_data.csv, plus pressure_kPa, spread_rate,
    direction, flags and low_flow_uncertain).

    - test_id is the part of the Lane A id after the first colon
      ("PSI-25:GMT50-B1" -> "B1", "paper-link2018:B13a-1" -> "B13a-1",
      "paper-saffire45:V-2" -> "V-2").
    - material is as recorded, EXCEPT rows below standard pressure
      (the Saffire V rows at 70.7–72.6 kPa): they stay labeled by
      pressure, e.g. "PMMA (Saffire V, 71.3 kPa)", so they never join
      the normal PMMA range. Saffire IV rows at 100.0 kPa are at
      standard pressure and keep their plain material name.
    - outcome "unknown" (and the two context-only PSI-100 rows, which
      have no O2 or outcome) becomes blank, Lane B's "unknown".
    - flow_start/flow_end are numbers or None; O12 and 7 other
      PSI-25 rows have no flow number at all.
    - low_flow_uncertain comes from Lane A's flags (their check
      covers both start and end flow — a row that ends at 0 cm/s is
      flagged even when it starts at 5, e.g. O13a). Spread rates are
      carried through but their unit is unresolved in Lane A's
      README — do not build spread-rate answers from them yet.
    """
    with open(path, encoding="utf-8") as f:
        tests = json.load(f)
    rows = []
    raw_sources = []
    for t in tests:
        # Short test ID: the Lane A id after the first colon, with the
        # PSI-25 GMT prefix stripped ("PSI-25:GMT50-B1" -> "B1").
        suffix = t.get("id", "").split(":", 1)[-1]
        gmt = re.match(r"GMT\d+-(.+)$", suffix)
        test_id = gmt.group(1) if gmt else suffix
        material = _canonical_material(t.get("material"))
        # Lane A records the Saffire V-2 cotton jersey as "other" (its
        # shape says cotton). Name it Cotton so "Will cotton burn ...?"
        # can find it (v11, Daksh). It still gets the pressure label
        # below, so it never joins a standard-pressure range.
        if material == "other" and "cotton" in (t.get("shape") or "").lower():
            material = "Cotton"
        pressure = t.get("pressure_kPa")
        if pressure is not None and pressure < STANDARD_PRESSURE_MIN_KPA:
            material = f"{material} (Saffire V, {pressure} kPa)"
        source_name, source_url = TESTS_SOURCES.get(
            t.get("source"), (t.get("source") or "", ""))
        outcome = t.get("outcome") or ""
        if outcome == "unknown":
            outcome = ""
        flow_start = t.get("flow_start")
        rows.append({
            "test_id": test_id,
            "material": material,
            "material_form": _form_from_shape(t.get("shape")),
            "oxygen_pct": ("" if t.get("o2_start") is None else t["o2_start"]),
            "airflow_cm_s": ("" if flow_start is None else flow_start),
            "airflow_end_cm_s": ("" if t.get("flow_end") is None else t["flow_end"]),
            "outcome": outcome,
            "outcome_source": (t.get("citation") or "" if outcome else ""),
            "source": source_name,
            "source_url": source_url,
            "notes": t.get("outcome_note") or "",
            "pressure_kPa": pressure,
            "spread_rate": t.get("spread_rate"),
            "direction": t.get("direction") or "",
            "flags": list(t.get("flags") or []),
            # Lane A's own flag, not a recomputation: theirs checks
            # both start and end flow, so a row that ends at 0 cm/s
            # (O13a, O15a, O15b) is flagged even when it starts at 5.
            "low_flow_uncertain": "low_flow_uncertain" in (t.get("flags") or []),
        })
        raw_sources.append(t.get("source"))
    # Disambiguate test IDs that collide across sources (PSI-98:S1 and
    # PSI-100:S1 both shorten to "S1"): prefix with the source's short
    # tag, e.g. "98-S1" and "100-S1".
    from collections import Counter
    counts = Counter(r["test_id"] for r in rows)
    for row, raw in zip(rows, raw_sources):
        if counts[row["test_id"]] > 1:
            tag = (raw or "x").split("-")[-1]
            row["test_id"] = f"{tag}-{row['test_id']}"
    return rows


def rows_from_full_csv(path):
    """Convert the full PSI-25 CSV into Lane B rows (same schema as
    sample_data.csv). Airflow comes from _parse_air_display (see
    above): pot settings and fan readings in the Air display column
    are skipped, so flow_start/flow_end are transducer readings in
    cm/s only. T25: 5 -> 2.5. O12 has no flow number at all."""
    rows = []
    with open(path, encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            flow_start, flow_end = _parse_air_display(
                r.get("Air display"), r.get("Flow restrictor"))
            group = group_name(r.get("Fuel Sample Material"))
            rows.append({
                "test_id": r.get("Test #"),
                "material": group,
                "material_form": _form_of(r.get("Fuel Sample Material"), group),
                "oxygen_pct": r.get("Calibrated  initial O2 % by vol "),
                "airflow_cm_s": _flow_str(flow_start),
                "airflow_end_cm_s": _flow_str(flow_end),
                "outcome": "",
                "source": "PSI-25",
                "source_url": PSI_25_URL,
                "notes": "",
                # No Lane A flags on this path (raw CSV), so compute it
                # the same way: below the 2 cm/s team cutoff at start
                # OR end (a test that ends at 0 is uncertain too).
                "low_flow_uncertain": bool(
                    (flow_start is not None and flow_start < LOW_FLOW_CUTOFF_CM_S)
                    or (flow_end is not None and flow_end < LOW_FLOW_CUTOFF_CM_S)),
            })
    return rows


def group_by_material(rows):
    """Group the rows by material, keeping the order they appear in."""
    grouped = defaultdict(list)
    for row in rows:
        grouped[row["material"]].append(row)
    return grouped


def _flow_text(row):
    start = row.get("airflow_cm_s")
    end = row.get("airflow_end_cm_s")
    if start in (None, ""):
        return None
    if end not in (None, "") and float(end) != float(start):
        return f"{start} -> {end} cm/s"
    return f"{start} cm/s"


def build_card(material, rows, dataset_max_o2=None):
    """Build one card from all the rows for one material.

    dataset_max_o2: the highest oxygen in the whole dataset, so a card
    can say whether it ties for the highest (PMMA / other and Nomex
    both reach 22.2%) instead of claiming it alone.
    """
    test_ids = [row["test_id"] for row in rows]
    forms = sorted({row["material_form"] for row in rows})
    # Some rows have no oxygen recorded (the two context-only Saffire
    # III rows) — skip them for the range instead of crashing.
    o2_values = [float(row["oxygen_pct"]) for row in rows
                 if row.get("oxygen_pct") not in (None, "")]
    o2_low = min(o2_values) if o2_values else None
    o2_high = max(o2_values) if o2_values else None
    n = len(rows)
    tests = "test" if n == 1 else "tests"
    form_text = " / ".join(forms)
    flows = sorted({f for f in (_flow_text(r) for r in rows) if f})

    if o2_low is None:
        o2_text = "oxygen not recorded"
    elif o2_low == o2_high:
        o2_text = f"{o2_high}% oxygen"
    else:
        o2_text = f"{o2_low}–{o2_high}% oxygen"
    # Airflow: list the values when there are few; summarise as a range
    # when there are many (the full-data card has dozens). The range
    # covers start AND end flows — a test that ramped to 38.5 cm/s
    # (O20) counts, not just its 5 cm/s start.
    flow_values = sorted({
        float(r["airflow_cm_s"])
        for r in rows if r.get("airflow_cm_s") not in (None, "")
    } | {
        float(r["airflow_end_cm_s"])
        for r in rows if r.get("airflow_end_cm_s") not in (None, "")
    })
    if not flows:
        flow_text = ""
    elif len(flows) <= 4:
        flow_text = f", airflow {', '.join(flows)}"
    elif flow_values:
        flow_text = f", airflow {min(flow_values)}–{max(flow_values)} cm/s"
    else:
        flow_text = ""

    # Sources: "BASS-II" only when every row is PSI-25; otherwise name
    # the investigations the rows actually come from.
    sources = sorted({row.get("source") or "" for row in rows} - {""})
    if sources == ["PSI-25"]:
        tested_in = "BASS-II"
    elif sources:
        tested_in = "microgravity (" + ", ".join(sources) + ")"
    else:
        tested_in = "microgravity"
    what_happened = (
        f"Tested in {tested_in}: {n} {tests} ({', '.join(test_ids)}) as {form_text} "
        f"at {o2_text}{flow_text}."
    )

    if o2_high is None:
        why_it_matters = (
            f"{material} has no oxygen value recorded in the dataset, "
            "so it cannot be used for oxygen-range questions."
        )
    elif dataset_max_o2 is not None and o2_high == dataset_max_o2:
        why_it_matters = (
            f"{material} was tested at the highest oxygen in the full "
            f"dataset ({o2_high}%), tied with the other materials that "
            f"reach {o2_high}%, so it is among the closest evidence we "
            "have for high-oxygen conditions."
        )
    elif o2_low <= 18.5:
        why_it_matters = (
            f"{material} was tested at the lower end of the full dataset "
            f"({o2_low}–{o2_high}% oxygen), so it is the mid-to-low-oxygen "
            "evidence for this material."
        )
    else:
        why_it_matters = (
            f"{material} was tested at {o2_low}–{o2_high}% oxygen, inside "
            "the tested range."
        )

    if sources == ["PSI-25"]:
        next_action = (
            "Check the BASS-II report Appendix A for the outcomes of "
            f"{', '.join(test_ids)}."
        )
    else:
        next_action = (
            "Check the cited source for each test for its outcome."
        )

    # Outcome counts exclude Link rows: they are paper rod data,
    # always burning, and Lane A's README says they don't count as
    # outcomes. PMMA is 76 of 102, not 130 of 154 (Daksh, Nov 14).
    outcome_rows = [r for r in rows
                    if "link" not in (r.get("source") or "").lower()]
    known = sum(1 for r in outcome_rows if r.get("outcome"))
    n_outcome = len(outcome_rows)
    if n_outcome and known == n_outcome:
        not_known = (
            "The test has a recorded outcome in the dataset." if n_outcome == 1
            else f"All {n_outcome} tests have a recorded outcome in the dataset."
        )
    elif known:
        not_known = (
            f"{known} of {n_outcome} {tests} have a recorded outcome; "
            f"{n_outcome - known} do not, and are not guessed."
        )
    else:
        not_known = (
            "No outcome is recorded for these tests in the dataset."
        )

    return {
        "material": material,
        "material_form": form_text,
        "test_ids": test_ids,
        "oxygen_range_pct": [o2_low, o2_high],
        "airflow_cm_s": flows,
        "what_happened": what_happened,
        "why_it_matters": why_it_matters,
        "next_action": next_action,
        "not_known": not_known,
        "source": ", ".join(sources) if sources else "PSI-25",
        "source_url": next(
            (TESTS_SOURCES[s][1] for s in sources if s in TESTS_SOURCES),
            PSI_25_URL),
    }


def build_cards(rows):
    """One card per material, in the order the materials first appear.
    The highest-oxygen line is computed across ALL rows, so ties are
    reported honestly."""
    grouped = group_by_material(rows)
    all_o2 = [float(r["oxygen_pct"]) for r in rows if r.get("oxygen_pct") not in (None, "")]
    dataset_max = max(all_o2) if all_o2 else None
    cards = []
    for material, mrows in grouped.items():
        card = build_card(material, mrows, dataset_max_o2=dataset_max)
        # Name the other materials tied at the max, when there are any.
        if dataset_max is not None and card["oxygen_range_pct"][1] == dataset_max:
            tied = sorted(
                m for m, rs in grouped.items()
                if m != material
                and any(r.get("oxygen_pct") not in (None, "") for r in rs)
                and max(float(r["oxygen_pct"]) for r in rs
                        if r.get("oxygen_pct") not in (None, "")) == dataset_max)
            if tied:
                card["why_it_matters"] = (
                    f"{material} was tested at the highest oxygen in the "
                    f"full dataset ({dataset_max}%), tied with "
                    f"{' and '.join(tied)}, so it is among the closest "
                    "evidence we have for high-oxygen conditions."
                )
        cards.append(card)
    return cards


def print_cards(cards):
    """Print the cards the way they will read on the website."""
    for card in cards:
        print(f"=== {card['material']} ({card['material_form']}) ===")
        print(f"What happened: {card['what_happened']}")
        print(f"Why it matters: {card['why_it_matters']}")
        print(f"Next action: {card['next_action']}")
        print(f"What's not known: {card['not_known']}")
        print(f"Source: {card['source_url']}")
        print()


if __name__ == "__main__":
    full_csv = os.path.join(os.path.dirname(__file__), "..", "data", "raw",
                            "PSI-25_Experimental table_BASS-II.csv")
    if os.path.exists(full_csv):
        rows = rows_from_full_csv(full_csv)
        print("(cards built from the full 129-row PSI-25 CSV)")
    else:
        rows = load_rows("sample_data.csv")
        print("(full PSI CSV not found — cards from the 6-row sample only; do not quote as dataset numbers)")
    cards = build_cards(rows)
    print_cards(cards)
    print(json.dumps(cards, indent=2))
