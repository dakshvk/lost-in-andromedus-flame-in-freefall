# Written with SI assistance (Muse), reviewed by Paridhi Singh
"""Lane B material cards — one card per material, four lines, no more.

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


def rows_from_full_csv(path):
    """Convert the full PSI-25 CSV into Lane B rows (same schema as
    sample_data.csv). Airflow = numbers in 'Air display' (transducer
    reading in cm/s): the first number is flow_start, the second when
    present is flow_end (T25: 5 -> 2.5). Non-numeric entries in that
    column ('no ign', 'see fan', '10 -> max') are ignored, never
    treated as flows."""
    rows = []
    with open(path, encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            air = re.findall(r"\d+(?:\.\d+)?", r.get("Air display") or "")
            group = group_name(r.get("Fuel Sample Material"))
            rows.append({
                "test_id": r.get("Test #"),
                "material": group,
                "material_form": _form_of(r.get("Fuel Sample Material"), group),
                "oxygen_pct": r.get("Calibrated  initial O2 % by vol "),
                "airflow_cm_s": air[0] if air else "",
                "airflow_end_cm_s": air[1] if len(air) > 1 else "",
                "outcome": "",
                "source": "PSI-25",
                "source_url": PSI_25_URL,
                "notes": "",
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
    if end not in (None, ""):
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
    o2_values = [float(row["oxygen_pct"]) for row in rows]
    o2_low, o2_high = min(o2_values), max(o2_values)
    n = len(rows)
    tests = "test" if n == 1 else "tests"
    form_text = " / ".join(forms)
    flows = sorted({f for f in (_flow_text(r) for r in rows) if f})

    if o2_low == o2_high:
        o2_text = f"{o2_high}% oxygen"
    else:
        o2_text = f"{o2_low}–{o2_high}% oxygen"
    # Airflow: list the values when there are few; summarise as a range
    # when there are many (the full-data card has dozens).
    flow_starts = sorted({
        float(r["airflow_cm_s"])
        for r in rows if r.get("airflow_cm_s") not in (None, "")
    })
    if not flows:
        flow_text = ""
    elif len(flows) <= 4:
        flow_text = f", airflow {', '.join(flows)}"
    elif flow_starts:
        flow_text = f", airflow {min(flow_starts)}–{max(flow_starts)} cm/s"
    else:
        flow_text = ""

    what_happened = (
        f"Tested in BASS-II: {n} {tests} ({', '.join(test_ids)}) as {form_text} "
        f"at {o2_text}{flow_text}."
    )

    if dataset_max_o2 is not None and o2_high == dataset_max_o2:
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

    next_action = (
        f"Check the BASS-II report Appendix A for the outcomes of "
        f"{', '.join(test_ids)}."
    )

    not_known = (
        "Outcome is not in the PSI-25 CSV — the card cannot say how long "
        "each test burned. Airflow is from the Air display column."
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
        "source": "PSI-25",
        "source_url": PSI_25_URL,
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
            tied = sorted(m for m, rs in grouped.items()
                          if max(float(r["oxygen_pct"]) for r in rs) == dataset_max and m != material)
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
