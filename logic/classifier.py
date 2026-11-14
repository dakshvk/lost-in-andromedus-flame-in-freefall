# Written with SI assistance (Muse), reviewed by Paridhi Singh
"""Lane B classifier — INSIDE / NEAR / BEYOND what NASA tested.

v2 changes (PR #1 review, Daksh):
- Airflow is NOT unknown: the PSI-25 CSV column "Air display" is the
  transducer reading in cm/s (BASS-II report NASA/TM-20210011385).
  Sample flow_start values come from the first number in that column.
- Ranges are per material, computed from the rows — never hard-coded.
  From the full 129-row dataset: SIBAL 16.4–20.8%, Nomex 21.0–22.2%,
  wax (F4, Japan Wax candle) 17.4% only. Overall: 13.6–22.2%.
- NEAR band is 1.0 point (per the doc Daksh cited; team decision,
  to be written in the limits drawer). That makes 24% O2 BEYOND,
  not NEAR — it was NEAR under the old 25.0 band.
- A missing oxygen value no longer returns BEYOND. It returns
  NEED_OXYGEN, so the answer asks for a value instead of answering.
- Airflow: 0–55 cm/s INSIDE (report max ~55, ~35 with two restrictors).
  55–65 cm/s is NEAR; above 65 is BEYOND.
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

    if material and rows:
        per_material = material_ranges(rows)
        if material in per_material:
            o2_min, o2_max = per_material[material]
            range_label = f"{material} {o2_min}–{o2_max}% O2"
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
