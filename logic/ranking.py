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

v9 changes (PR #1 review, Daksh, Nov 14):
- main() no longer writes the scores back into Lane A's
  experiments.json. The scores live in logic/ranked_experiments.json
  and the web lane reads that file; writing back made every Lane B
  run a change to a file Jenisha owns.

v8 change (PR #1 review, Daksh, Nov 14): the fire-safety +3 is a
team call, not an exact-text match. It goes to any sub-research area
that mentions "fire" (so "Spacecraft Fire, Smoke Distribution" and
"Fire Safety" count), plus all three Saffire experiments (PSI-98,
PSI-99, PSI-100) as one NASA project — Saffire II's page says
"Surface Combustion", which mentions no fire. The rule is written in
RANKING_NOTE, next to the judgement line, so the page shows it.

Run from inside logic/:
    python3 ranking.py
Reads ../data/experiments.json (Lane A's file — its score fields are
left blank "for Lane B to score") and writes ranked_experiments.json
(sorted, with rank) for the website. Lane A's file is NOT modified:
the scores live in logic/ranked_experiments.json, and the web lane
reads that file (Daksh, Nov 14).
"""

import json
import os

EXPERIMENTS_PATH = os.path.join(
    os.path.dirname(__file__), "..", "data", "experiments.json")
RANKED_PATH = os.path.join(os.path.dirname(__file__), "ranked_experiments.json")

# The three Saffire experiments are one NASA project; they get the
# fire-safety +3 even when their sub-area does not mention fire
# (Saffire II's page says "Surface Combustion"). Team call, Nov 14.
SAFFIRE_IDS = {"PSI-98", "PSI-99", "PSI-100"}
RANKING_NOTE = (
    "Scored by Lane B (Paridhi Singh), Nov 14, 2026. "
    "This ranking is the team's judgement, not NASA's. "
    "Fire-safety +3 goes to any sub-area mentioning 'fire', plus all "
    "three Saffire experiments (PSI-98, PSI-99, PSI-100) as one NASA "
    "project — a team call, not NASA's."
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

    # 2. Research area is spacecraft fire safety +3. Team call
    #    (Nov 14): the +3 goes to any sub-area that mentions "fire",
    #    plus all three Saffire experiments as one NASA project.
    #    "Flames ..." does not contain "fire", so ACME stays at 0.
    sub = exp.get("sub_research_area")
    if sub is not None and "fire" in sub.lower():
        breakdown.append({"reason": "sub-research area mentions fire", "points": 3})
    elif exp.get("psi_id") in SAFFIRE_IDS:
        breakdown.append({"reason": "Saffire experiment — one NASA project", "points": 3})
    elif sub is None:
        breakdown.append({"reason": "sub-research area missing", "points": 0})
        notes.append("sub_research_area missing")
    else:
        breakdown.append({"reason": f"sub-research area is {sub}, not fire-related", "points": 0})

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
    dicts carry a "rank" field; they are written to
    ranked_experiments.json by main() — Lane A's experiments.json is
    never modified (its score fields stay blank; the web lane reads
    the ranked file)."""
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
    # Only the ranked file is written. Lane A's experiments.json is
    # read-only here — its score fields stay blank, and the web lane
    # reads logic/ranked_experiments.json for the scores (Daksh,
    # Nov 14). Writing the scores back into Lane A's file would make
    # every Lane B run a change to a file Jenisha owns, and merge
    # against her updates.
    with open(RANKED_PATH, "w", encoding="utf-8") as f:
        json.dump(ranked, f, indent=2)
    print(f"{RANKING_NOTE}\n")
    for exp in ranked:
        print(f"{exp['rank']:>2}. {exp['psi_id']} — {exp['title'][:60]} "
              f"— score {exp['score']} (tests: {exp.get('test_count')})")
    return ranked


if __name__ == "__main__":
    main()
