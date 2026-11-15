# Written with SI assistance (Muse), reviewed by Paridhi Singh
"""Lane B classifier — INSIDE / NEAR / BEYOND what NASA tested.

v7 changes (Lane A swap, Nov 14):
- No code change needed for the swap: the pressure-labeled Saffire V
  rows ("PMMA (Saffire V, 71.3 kPa)") form their own material groups,
  so they never join the plain PMMA range; the too-few-rows rule
  marks them extrapolated (1 row each).

v6 changes (PR #1 review, Daksh, Nov 14):
- Airflow parser (cards._parse_air_display): the Air display column
  mixes transducer readings with fan-pot settings and fan readings.
  Pot settings (~0.3–2.7) appear after "pot"/"pots", as "0.5 pot",
  or in parentheses (P14 ".85", P3b "0.85", P15 "0.36"); fan
  readings are 40–62 (O5a "(49, 62, 49, 44, 42)", O5b "49", O13a
  "49, 44, 42, ..."). With two restrictors the duct caps at about
  35 cm/s, with fewer at about 55, so numbers above the cap are fan
  readings. The old parser took the first number, so "highest
  airflow 49 cm/s (O5b, O13a)" and "P14 ends at 85 cm/s" were pot
  and fan readings, not flows. O5b's real flow is 5 cm/s (report:
  "Fan pot 1.3 (5 cm/s)"); O13a's real flows are (5, 2, 0). T21's
  "11 to 47" and T17's "6 to 53" are real flows (report Table 7.1).
  flow_end is now the LAST number in the sequence (a ramp like B10
  "5 4 3 2 1" ends at 1, not 4).
- classify(): oxygen outside 0–100% returns INVALID (not a possible
  oxygen level); a material with fewer than 3 rows on a real dataset
  (20+ rows) returns BEYOND (extrapolated) — the rule does not apply
  to the 6-row sample. flow_range() returns the (min, max) flow_start
  across rows, skipping rows with no numeric flow_start (O12).
"""

# Fallbacks only — used when no rows are passed in. Real ranges always
# come from material_ranges(rows) / dataset_range(rows) below.
DEFAULT_O2_MIN = 13.6
DEFAULT_O2_MAX = 22.2
AIRFLOW_MAX = 55.0
NEAR_AIRFLOW_MAX = 65.0
NEAR_POINTS = 1.0


def _o2(row):
    try:
        return float(row["oxygen_pct"])
    except (KeyError, TypeError, ValueError):
        return None


def material_ranges(rows):
    """O2 min/max per material, computed from the rows given.

    Returns {"PMMA": (low, high), "SIBAL": (low, high), ...}.
    Rows with no usable O2 are skipped.
    """
    ranges = {}
    for row in rows:
        value = _o2(row)
        if value is None:
            continue
        material = row.get("material")
        if material not in ranges:
            ranges[material] = [value, value]
        else:
            ranges[material][0] = min(ranges[material][0], value)
            ranges[material][1] = max(ranges[material][1], value)
    return {k: (v[0], v[1]) for k, v in ranges.items()}


def dataset_range(rows):
    """Overall O2 min/max across all rows given."""
    values = [v for v in (_o2(r) for r in rows) if v is not None]
    if not values:
        return (DEFAULT_O2_MIN, DEFAULT_O2_MAX)
    return (min(values), max(values))


def flow_range(rows):
    """(min, max) flow_start across rows, skipping rows with no
    numeric flow_start (e.g. O12, "no ign at any flow"). Returns
    (None, None) when no row has one."""
    values = []
    for row in rows:
        try:
            values.append(float(row["airflow_cm_s"]))
        except (KeyError, TypeError, ValueError):
            continue
    if not values:
        return (None, None)
    return (min(values), max(values))


def _same_material(a, b):
    """"PMMA" and "PMMA / other" are the same group (the full-data
    grouping); other names match exactly."""
    if a == b:
        return True
    return {a, b} == {"PMMA", "PMMA / other"}


def classify(oxygen_pct, airflow_cm_s=None, material=None, rows=None):
    """Return a dict with verdict, reason, and what is unknown.

    oxygen_pct: float, or None. None -> verdict NEED_OXYGEN.
    airflow_cm_s: float or None. None = not given for this question.
    material: e.g. "SIBAL" — when given (with rows), the verdict uses
        that material's tested O2 range instead of the overall range.
    rows: the frozen rows, used to compute the ranges. When omitted,
        the overall 13.6–22.2% fallback range is used.
    """
    if oxygen_pct is None:
        return {
            "verdict": "NEED_OXYGEN",
            "reason": "No oxygen value was given, so there is nothing to classify — ask for an oxygen value first.",
            "unknown": ["oxygen_pct"],
        }

    oxygen_pct = float(oxygen_pct)
    rows = rows or []

    # Oxygen outside 0–100% is not a possible oxygen level at all —
    # it is invalid input, not a point beyond the tested range.
    if oxygen_pct < 0 or oxygen_pct > 100:
        return {
            "verdict": "INVALID",
            "reason": f"{oxygen_pct}% oxygen is not a possible oxygen level — oxygen must be between 0 and 100%.",
            "unknown": [],
        }

    if material and rows:
        per_material = material_ranges(rows)
        # "PMMA" and "PMMA / other" are the same group, so match
        # with _same_material rather than an exact key lookup.
        matched = next((k for k in per_material if _same_material(k, material)), None)
        if matched is not None:
            o2_min, o2_max = per_material[matched]
            range_label = f"{material} {o2_min}–{o2_max}% O2"
            # Fewer than 3 rows for a material means extrapolated,
            # not covered — but only on a real dataset (20+ rows).
            # The 6-row sample is explicitly a sample, so the rule
            # does not apply to it.
            if len(rows) >= 20:
                count = sum(1 for r in rows if _same_material(r.get("material"), material))
                if count < 3:
                    return {
                        "verdict": "BEYOND",
                        "reason": f"Only {count} {material} row(s) in the dataset — fewer than 3, so this is extrapolated, not covered.",
                        "unknown": [f"more {material} rows"],
                    }
        else:
            return {
                "verdict": "BEYOND",
                "reason": f"No {material} rows in the dataset, so this cannot be classified from the data.",
                "unknown": [f"rows for {material}"],
            }
    elif rows:
        o2_min, o2_max = dataset_range(rows)
        range_label = f"{o2_min}–{o2_max}% O2"
    else:
        o2_min, o2_max = DEFAULT_O2_MIN, DEFAULT_O2_MAX
        range_label = f"{o2_min}–{o2_max}% O2"

    unknown = []
    if airflow_cm_s is None:
        unknown.append("airflow_cm_s (not given for this question)")

    o2_far = oxygen_pct < o2_min - NEAR_POINTS or oxygen_pct > o2_max + NEAR_POINTS
    o2_outside = oxygen_pct < o2_min or oxygen_pct > o2_max
    air_outside = airflow_cm_s is not None and (
        float(airflow_cm_s) < 0 or float(airflow_cm_s) > AIRFLOW_MAX
    )
    air_far = airflow_cm_s is not None and float(airflow_cm_s) > NEAR_AIRFLOW_MAX

    if o2_far or air_far:
        verdict = "BEYOND"
        if o2_far and air_far:
            reason = (
                f"{oxygen_pct}% O2 and {airflow_cm_s} cm/s airflow are both "
                f"clearly outside the tested range ({range_label}, "
                f"0–{AIRFLOW_MAX} cm/s)."
            )
        elif o2_far:
            reason = (
                f"{oxygen_pct}% O2 is clearly outside the tested range "
                f"({range_label})."
            )
        else:
            reason = (
                f"{airflow_cm_s} cm/s airflow is clearly above the tested "
                f"maximum of ~{AIRFLOW_MAX} cm/s."
            )
    elif o2_outside or air_outside:
        verdict = "NEAR"
        if o2_outside and air_outside:
            reason = (
                f"{oxygen_pct}% O2 and {airflow_cm_s} cm/s airflow are both "
                f"just outside the tested range ({range_label}, "
                f"0–{AIRFLOW_MAX} cm/s)."
            )
        elif o2_outside:
            reason = (
                f"{oxygen_pct}% O2 is just outside the tested range "
                f"({range_label}); the closest tested rows are at the edge."
            )
        else:
            reason = (
                f"{airflow_cm_s} cm/s airflow is just above the tested maximum "
                f"of ~{AIRFLOW_MAX} cm/s."
            )
    else:
        verdict = "INSIDE"
        reason = (
            f"{oxygen_pct}% O2 is inside the tested range ({range_label})."
        )

    return {"verdict": verdict, "reason": reason, "unknown": unknown}
