# Written with SI assistance (Claude), reviewed by Paridhi Singh
"""Lane B material cards — one card per material, four lines, no more.

Template (from the Lane B starter):
- What happened: one plain sentence from the rows.
- Why it matters: one sentence for a mission planner.
- Next action: what a planner should check next.
- What's not known: the gap, stated plainly.

Every number on a card comes from the rows in sample_data.csv.
Outcomes and airflow are NOT on the cards yet — they are not in the
PSI-25 CSV, so the card says so instead of guessing.
"""

import json
from collections import defaultdict

from answer import load_rows

PSI_25_URL = "https://psi.nasa.gov/physci/repo/data/investigations/PSI-25"


def group_by_material(rows):
    """Group the rows by material, keeping the order they appear in."""
    grouped = defaultdict(list)
    for row in rows:
        grouped[row["material"]].append(row)
    return grouped


def build_card(material, rows):
    """Build one card from all the rows for one material."""
    test_ids = [row["test_id"] for row in rows]
    forms = sorted({row["material_form"] for row in rows})
    o2_values = [float(row["oxygen_pct"]) for row in rows]
    o2_low, o2_high = min(o2_values), max(o2_values)
    n = len(rows)
    tests = "test" if n == 1 else "tests"
    form_text = " / ".join(forms)

    if o2_low == o2_high:
        o2_text = f"{o2_high}% oxygen"
    else:
        o2_text = f"{o2_low}–{o2_high}% oxygen"

    what_happened = (
        f"Tested in BASS-II: {n} {tests} ({', '.join(test_ids)}) as {form_text} "
        f"at {o2_text}."
    )

    # "Why it matters" is only what the rows themselves support:
    # where this material sits in the tested range.
    if o2_high >= 22.2:
        why_it_matters = (
            f"{material} was tested at the highest oxygen in the sample "
            f"({o2_high}%), so it is the closest evidence we have for "
            "high-oxygen conditions."
        )
    elif o2_low <= 18.5:
        why_it_matters = (
            f"{material} was tested at the lower end of the sample "
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
        f"{', '.join(test_ids)}, and the fan calibration file for airflow in cm/s."
    )

    not_known = (
        "Outcome and airflow in cm/s are not in the PSI-25 CSV — "
        "the card cannot say how long each test burned, or at what airflow."
    )

    return {
        "material": material,
        "material_form": form_text,
        "test_ids": test_ids,
        "oxygen_range_pct": [o2_low, o2_high],
        "what_happened": what_happened,
        "why_it_matters": why_it_matters,
        "next_action": next_action,
        "not_known": not_known,
        "source": "PSI-25",
        "source_url": PSI_25_URL,
    }


def build_cards(rows):
    """One card per material, in the order the materials first appear."""
    return [build_card(material, mrows) for material, mrows in group_by_material(rows).items()]


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
    rows = load_rows("sample_data.csv")
    cards = build_cards(rows)
    print_cards(cards)
    print(json.dumps(cards, indent=2))
