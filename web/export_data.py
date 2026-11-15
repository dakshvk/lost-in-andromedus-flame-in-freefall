# Written with SI assistance (Claude Code), reviewed by Daksh Kumar
"""Lane C data export: turn Lane A's data and Lane B's logic into the
JSON files the website reads. No design here, only data.

Run from the repo root (or anywhere):
    python3 web/export_data.py

Writes web/data/:
    tests.json           one point per test, for the evidence map
    cards.json           one card per material (structured numbers only)
    experiments.json     the 24 ranked PSI investigations, with reasons
    investigations.json  the 10 investigations with objective/fuels/sensors
    limits.json          every threshold and rule the site must show
    demo_answers.json    saved answers, the fallback when the API is down
    meta.json            counts, so the page and the data can be checked

Every number comes from Lane A's data/tests.json through Lane B's code.
Nothing is typed in here except the hardware groups, which are copied
from NASA's challenge notes (source given in the file).
"""

import json
import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
LOGIC = os.path.join(ROOT, "logic")
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(ROOT, "web", "data")
sys.path.insert(0, LOGIC)

from answer import GRAVITY_NOTE, gravity_note  # noqa: E402
from cards import (LOW_FLOW_CUTOFF_CM_S, STANDARD_PRESSURE_MIN_KPA,  # noqa: E402
                   rows_from_tests_json)
from classifier import (AIRFLOW_MAX, FLOW_MARGIN, NEAR_AIRFLOW_MAX,  # noqa: E402
                        NEAR_POINTS, flow_range)
from rag import CUTOFF, load_investigations  # noqa: E402
from ranking import RANKING_NOTE  # noqa: E402

TESTS_JSON = os.path.join(DATA, "tests.json")
OUTCOMES = ["quenched", "blow_off", "burning", "no_ignition", "ignited_only", "unknown"]

# Copied from NASA's Flame in Freefall challenge notes ("Hardware"):
# BASS, BASS-II, SPICE and SLICE used the MSG flow duct built for SPICE;
# the ACME experiments used the CIR; FLEX, FLEX-2 and CFI used the MDCA.
HARDWARE = {
    "BASS": "Microgravity Science Glovebox (MSG), SPICE flow duct",
    "BASS-II": "Microgravity Science Glovebox (MSG), SPICE flow duct",
    "ACME-BRE": "Combustion Integrated Rack (CIR), ACME hardware",
    "ACME-CLD": "Combustion Integrated Rack (CIR), ACME hardware",
    "FLEX": "Multi-user Droplet Combustion Apparatus (MDCA) in the CIR",
}
HARDWARE_SOURCE = "NASA Space Apps 2026, Flame in Freefall challenge notes (Hardware)"


def _is_link(row):
    return "link" in (row.get("source") or "").lower()


def _has_o2(row):
    return row.get("oxygen_pct") not in (None, "")


def export_tests(lane_a, rows):
    """Map points. Lane A's rows carry the citation and notes; Lane B's
    rows carry the canonical material name (Cotton, Wax, Saffire V
    pressure labels). Both lists are in the same order."""
    out = []
    for a, b in zip(lane_a, rows):
        flags = a.get("flags") or []
        out.append({
            "id": a["id"],
            "test_id": b["test_id"],
            "material": b["material"],
            "shape": a.get("shape"),
            "source": a["source"],
            "o2_start": a.get("o2_start"),
            "o2_end": a.get("o2_end"),
            "flow_start": a.get("flow_start"),
            "flow_end": a.get("flow_end"),
            "direction": a.get("direction"),
            "outcome": a.get("outcome"),
            "outcome_note": a.get("outcome_note"),
            "pressure_kPa": a.get("pressure_kPa"),
            "spread_rate": a.get("spread_rate"),
            "flow_note": a.get("flow_note"),
            "low_flow_uncertain": "low_flow_uncertain" in flags,
            "low_pressure": (a.get("pressure_kPa") is not None
                             and a["pressure_kPa"] < STANDARD_PRESSURE_MIN_KPA),
            "context_only": "context_only" in flags,
            "is_link2018": a["source"] == "paper-link2018",
            "flags": flags,
            "citation": a.get("citation"),
        })
    return out


def _card(material, group, rows):
    """One card. Counts and ranges use rows that are not Link et al.
    (paper rod data, a different flow calibration, never outcome
    evidence) and that have an oxygen value."""
    mine = [r for r in rows if r["material"] == material]
    evidence = [r for r in mine if not _is_link(r) and _has_o2(r)]
    outcomes = {k: 0 for k in OUTCOMES}
    for r in evidence:
        outcomes[r["outcome"] or "unknown"] += 1
    o2 = [float(r["oxygen_pct"]) for r in evidence]
    flo, fhi = flow_range(evidence)
    sources = {}
    for r in evidence:
        sources[r["source"]] = r["source_url"]
    pressures = sorted({r["pressure_kPa"] for r in evidence if r.get("pressure_kPa") is not None})
    slug = "".join(ch if ch.isalnum() else "-" for ch in material.lower()).strip("-")
    while "--" in slug:
        slug = slug.replace("--", "-")
    return {
        "id": slug,
        "material": material,
        "group": group,
        "forms": sorted({r["material_form"] for r in evidence if r.get("material_form")}),
        "test_count": len(evidence),
        "known_outcomes": len(evidence) - outcomes["unknown"],
        "outcomes": outcomes,
        "oxygen_range_pct": [min(o2), max(o2)] if o2 else None,
        "airflow_range_cm_s": [flo, fhi] if flo is not None else None,
        "pressure_kPa": pressures,
        "too_few": len(evidence) < 3,
        "low_flow_uncertain_tests": sum(1 for r in evidence if r.get("low_flow_uncertain")),
        "link2018_rows": sum(1 for r in mine if _is_link(r)),
        "test_ids": [r["test_id"] for r in evidence],
        "sources": [{"name": n, "url": u} for n, u in sorted(sources.items())],
    }


def export_cards(rows):
    """Standard-pressure materials get their own card. The Saffire V
    rows (~71 kPa) go in one low-pressure group card, as the team
    decided, so they never look like part of a normal range."""
    standard = sorted({r["material"] for r in rows if "(Saffire V," not in r["material"]})
    low = sorted({r["material"] for r in rows if "(Saffire V," in r["material"]})
    return {
        "cards": [_card(m, "standard", rows) for m in standard],
        "low_pressure_group": {
            "title": "Low-pressure tests (Saffire V)",
            "note": ("These tests ran at about 71 kPa, not normal cabin pressure, "
                     "so they are kept out of every standard range."),
            "cards": [_card(m, "low_pressure", rows) for m in low],
        },
        "counting_rule": ("Counts and ranges exclude Link et al. 2018 rows (paper rod "
                          "data, different flow calibration, not outcome evidence) and "
                          "rows with no oxygen value."),
    }


def export_experiments():
    with open(os.path.join(LOGIC, "ranked_experiments.json"), encoding="utf-8") as f:
        ranked = json.load(f)
    keep = ["rank", "psi_id", "title", "url", "research_area", "sub_research_area",
            "project_type", "fuel_type", "gravity", "is_flight", "has_data_table",
            "test_count", "test_count_source", "summary", "score", "score_breakdown",
            "doi", "license"]
    return {"note": RANKING_NOTE,
            "experiments": [{k: e.get(k) for k in keep} for e in ranked]}


def export_investigations():
    out = []
    for inv in load_investigations():
        row = dict(inv)
        row["hardware"] = HARDWARE.get(inv["id"])
        row["hardware_source"] = HARDWARE_SOURCE if inv["id"] in HARDWARE else None
        out.append(row)
    return out


def export_limits(rows):
    return {
        "near_margin_oxygen_points": NEAR_POINTS,
        "near_margin_flow_fraction": FLOW_MARGIN,
        "low_flow_cutoff_cm_s": LOW_FLOW_CUTOFF_CM_S,
        "standard_pressure_min_kPa": STANDARD_PRESSURE_MIN_KPA,
        "duct_airflow_max_cm_s": AIRFLOW_MAX,
        "duct_airflow_near_max_cm_s": NEAR_AIRFLOW_MAX,
        "rag_score_cutoff": CUTOFF,
        "gravity_note": gravity_note(rows),
        "gravity_note_short": GRAVITY_NOTE,
        "rules": [
            "A test whose flow changed covers its whole span, from start to end flow.",
            "NEAR means just outside the tested range: 1.0 oxygen point, or 25% of the material's flow range.",
            "Fewer than 3 tests for a material means extrapolated, not covered.",
            "Flows under 2 cm/s are flagged as uncertain (team choice: the BASS-II report says low flows have high error bars but gives no number).",
            "If the crew turned the flow off and the flame went out, the outcome is unknown, not quenched.",
            "Saffire V tests (about 71 kPa) are kept out of the standard ranges and shown by pressure.",
            "Link et al. 2018 rows are paper rod data: not outcome evidence, different flow calibration.",
            "Outcomes that are not recorded are shown as unknown, never guessed.",
        ],
        "ranking_note": RANKING_NOTE,
        "si_acknowledgment": ("Data extraction, logic and code were written with SI assistance "
                      "(Claude, Claude Code, Muse, Cursor) and reviewed by the team. "
                      "See AI_USE_LOG.md."),
        "license": "PSI data is CC0 (NASA Physical Sciences Informatics).",
    }


def export_demo_answers():
    with open(os.path.join(LOGIC, "demo_answers.json"), encoding="utf-8") as f:
        return json.load(f)


def build_all():
    """Return every export as {filename: payload}, without writing."""
    with open(TESTS_JSON, encoding="utf-8") as f:
        lane_a = json.load(f)
    rows = rows_from_tests_json(TESTS_JSON)
    assert len(lane_a) == len(rows), "Lane A and Lane B row counts differ"
    files = {
        "tests.json": export_tests(lane_a, rows),
        "cards.json": export_cards(rows),
        "experiments.json": export_experiments(),
        "investigations.json": export_investigations(),
        "limits.json": export_limits(rows),
        "demo_answers.json": export_demo_answers(),
    }
    files["meta.json"] = {
        "tests": len(files["tests.json"]),
        "cards": len(files["cards.json"]["cards"]),
        "low_pressure_cards": len(files["cards.json"]["low_pressure_group"]["cards"]),
        "experiments": len(files["experiments.json"]["experiments"]),
        "investigations": len(files["investigations.json"]),
        "demo_answers": len(files["demo_answers.json"]["answers"]),
        "built_from": ["data/tests.json (Lane A)", "logic/ (Lane B)"],
    }
    return files


def main():
    files = build_all()
    os.makedirs(OUT, exist_ok=True)
    for name, payload in files.items():
        with open(os.path.join(OUT, name), "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=1, ensure_ascii=False)
            f.write("\n")
    print("wrote", ", ".join(files), "to web/data/")
    print("counts:", files["meta.json"])


if __name__ == "__main__":
    main()
