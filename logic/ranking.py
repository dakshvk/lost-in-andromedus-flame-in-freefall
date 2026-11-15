# Written with SI assistance (Muse), reviewed by Paridhi Singh
"""Lane B ranking — score each PSI experiment for the dashboard.

Team doc, Part 4, Step 2. Score each experiment as a sum of points
from its PSI record:
    solid fuel +3
    research area is spacecraft fire safety +3
    has a data table +2
    is a flight experiment +2
    microgravity +1
    20 or more tests +1
Output: score and score_breakdown, e.g.
[{"reason": "solid fuel", "points": 3}, ...].
Ties break by test count, then alphabetically (by title).
The ranking is the team's judgement, not NASA's — the page must say so.
If a field is missing, give 0 and note "missing", never guess.

Run from inside logic/:
    python3 ranking.py
Reads ../data/experiments.json (Lane A's file — its score fields are
left blank "for Lane B to score"), fills in score / score_breakdown /
score_note for every row, writes the file back, and writes
ranked_experiments.json (sorted, with rank) for the website.
"""

import json
import os

EXPERIMENTS_PATH = os.path.join(
    os.path.dirname(__file__), "..", "data", "experiments.json")
RANKED_PATH = os.path.join(os.path.dirname(__file__), "ranked_experiments.json")

FIRE_SAFETY = "Spacecraft Fire Safety"
RANKING_NOTE = (
    "Scored by Lane B (Paridhi Singh), Nov 14, 2026. "
    "This ranking is the team's judgement, not NASA's."
)


def score_experiment(exp):
    """Score one experiment dict. Returns (score, breakdown, notes).

    breakdown is a list of {"reason", "points"} — one entry per rule,
    including the 0-point rules, so the page can show why an
    experiment ranked where it did. A missing field scores 0 and is
    noted as "missing"; a field that is present but does not meet the
    rule scores 0 and names what it actually is.
    """
    breakdown = []
    notes = []

    # 1. Solid fuel +3.
    fuel = exp.get("fuel_type")
    if fuel == "solid":
        breakdown.append({"reason": "solid fuel", "points": 3})
    elif fuel is None:
        breakdown.append({"reason": "fuel type missing", "points": 0})
        notes.append("fuel_type missing")
    else:
        breakdown.append({"reason": f"fuel type is {fuel}, not solid", "points": 0})

    # 2. Research area is spacecraft fire safety +3. The rule is
    #    applied to the sub-area as stored: only the exact wording
    #    "Spacecraft Fire Safety" counts. Near misses ("Spacecraft
    #    Fire, Smoke Distribution", "Fire Safety", "Surface
    #    Combustion") do not — the team can overrule that call.
    sub = exp.get("sub_research_area")
    if sub == FIRE_SAFETY:
        breakdown.append({"reason": "research area is spacecraft fire safety", "points": 3})
    elif sub is None:
        breakdown.append({"reason": "sub-research area missing", "points": 0})
        notes.append("sub_research_area missing")
    else:
        breakdown.append({"reason": f"sub-research area is {sub}, not spacecraft fire safety", "points": 0})

    # 3. Has a data table +2.
    table = exp.get("has_data_table")
    if table is True:
        breakdown.append({"reason": "has a data table", "points": 2})
    elif table is None:
        breakdown.append({"reason": "data table missing", "points": 0})
        notes.append("has_data_table missing")
    else:
        breakdown.append({"reason": "no data table", "points": 0})

    # 4. Is a flight experiment +2.
    flight = exp.get("is_flight")
    if flight is True:
        breakdown.append({"reason": "flight experiment", "points": 2})
    elif flight is None:
        breakdown.append({"reason": "flight status missing", "points": 0})
        notes.append("is_flight missing")
    else:
        breakdown.append({"reason": "not a flight experiment", "points": 0})

    # 5. Microgravity +1.
    gravity = exp.get("gravity")
    if gravity == "micro":
        breakdown.append({"reason": "microgravity", "points": 1})
    elif gravity is None:
        breakdown.append({"reason": "gravity missing", "points": 0})
        notes.append("gravity missing")
    else:
        breakdown.append({"reason": f"gravity is {gravity}, not microgravity", "points": 0})

    # 6. 20 or more tests +1. test_count None scores 0 ("missing").
    #    Caveat, from Lane A's README: some counts are day summaries,
    #    not single burns (PSI-21, PSI-22), and PSI-101's 110 differs
    #    from the page's "66 test points" (not reconciled). The point
    #    is still given when the recorded count is 20+, because a day
    #    summary covers several burns; the caveat is in the note so
    #    the team can see it and overrule.
    count = exp.get("test_count")
    if count is None:
        breakdown.append({"reason": "test count missing", "points": 0})
        notes.append("test_count missing")
    elif count >= 20:
        breakdown.append({"reason": f"{count} tests (20 or more)", "points": 1})
    else:
        breakdown.append({"reason": f"only {count} tests (fewer than 20)", "points": 0})

    score = sum(b["points"] for b in breakdown)
    return score, breakdown, notes


def rank_experiments(experiments):
    """Score every experiment and return them sorted: score desc,
    test count desc (missing counts last), title A–Z. The returned
    dicts carry a "rank" field; the experiments.json write-back in
    main() strips it, so Lane A's file keeps its own order with the
    scores filled in."""
    scored = []
    for exp in experiments:
        score, breakdown, notes = score_experiment(exp)
        exp = dict(exp)
        exp["score"] = score
        exp["score_breakdown"] = breakdown
        note = RANKING_NOTE
        if notes:
            note += " Missing fields: " + "; ".join(notes) + "."
        source = exp.get("test_count_source") or ""
        if "day" in source.lower() and "not single burns" in source.lower():
            note += (" Test count is day summaries, not single burns "
                     "(see test_count_source).")
        if exp.get("psi_id") == "PSI-101":
            note += (" Test count 110 differs from the page's "
                     "'66 test points' (not reconciled).")
        exp["score_note"] = note
        scored.append(exp)
    scored.sort(key=lambda e: (
        -e["score"],
        -(e["test_count"] if e.get("test_count") is not None else -1),
        e.get("title") or "",
    ))
    for i, exp in enumerate(scored, start=1):
        exp["rank"] = i
    return scored


def main():
    with open(EXPERIMENTS_PATH, encoding="utf-8") as f:
        experiments = json.load(f)
    ranked = rank_experiments(experiments)
    # Write the scores back into Lane A's file in its original order
    # (its score fields were left blank for Lane B), and write the
    # sorted list with ranks for the site.
    by_id = {e["psi_id"]: e for e in ranked}
    scored_in_order = []
    for exp in experiments:
        updated = dict(by_id[exp["psi_id"]])
        updated.pop("rank", None)
        scored_in_order.append(updated)
    with open(EXPERIMENTS_PATH, "w", encoding="utf-8") as f:
        json.dump(scored_in_order, f, indent=2)
    with open(RANKED_PATH, "w", encoding="utf-8") as f:
        json.dump(ranked, f, indent=2)
    print(f"{RANKING_NOTE}\n")
    for exp in ranked:
        print(f"{exp['rank']:>2}. {exp['psi_id']} — {exp['title'][:60]} "
              f"— score {exp['score']} (tests: {exp.get('test_count')})")
    return ranked


if __name__ == "__main__":
    main()
