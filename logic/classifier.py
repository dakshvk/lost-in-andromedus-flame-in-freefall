# Written with SI assistance (Muse), reviewed by Paridhi Singh
"""Lane B classifier — INSIDE / NEAR / BEYOND what NASA tested.

v10 changes (PR #1 review, Daksh, Nov 14):
- The too-few-rows and no-rows BEYOND returns now carry a "coverage"
  key, so build_answer can use the coverage sentence instead of the
  generic "both beyond" one (which would name an airflow that was
  never given, "None cm/s").
- The 25% margin definition (25% of the range width, both sides, low
  clamped at 0) is now CONFIRMED by Daksh — no longer a proposal.

v9 changes (PR #1 review, Daksh, Nov 14):
- classify() now uses each material's own tested flow range with a
  25% margin (doc Step 1 items 3 and 4), not the hardware limit for
  every material. PMMA was tested at 0–20 cm/s, so 45 cm/s for PMMA
  is BEYOND (the margin runs to 25 cm/s); the hardware band
  (0–55 cm/s, NEAR up to 65) is only the fallback when no material
  is given or the material has no flow data. The margin is 25% of
  the range width, on both sides (low side clamped at 0).
- flow_range() is now used by classify() (it had no production
  caller) via the new material_flow_range() helper.

v8 changes (PR #1 review, Daksh, Nov 14):
- flow_range() now uses the whole span: a test whose flow changed
  covers its whole span, so each row contributes the lower and higher
  of its flow_start and flow_end (rows with no numeric flow_start,
  e.g. O12, are still skipped).

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
# The doc's margin on a material's tested flow range (Step 1 items 3
# and 4): 25% of the range width, on both sides.
FLOW_MARGIN = 0.25


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
    """(min, max) flow across rows. A test whose flow changed covers
    its whole span, so a row contributes the lower and higher of its
    flow_start and flow_end. Rows with no numeric flow_start (e.g.
    O12, "no ign at any flow") are skipped. Returns (None, None)
    when no row has one."""
    lows, highs = [], []
    for row in rows:
        try:
            start = float(row["airflow_cm_s"])
        except (KeyError, TypeError, ValueError):
            continue
        values = [start]
        try:
            values.append(float(row["airflow_end_cm_s"]))
        except (KeyError, TypeError, ValueError):
            pass
        lows.append(min(values))
        highs.append(max(values))
    if not lows:
        return (None, None)
    return (min(lows), max(highs))


def _same_material(a, b):
    """"PMMA" and "PMMA / other" are the same group (the full-data
    grouping); other names match exactly."""
    if a == b:
        return True
    return {a, b} == {"PMMA", "PMMA / other"}


def material_flow_range(rows, material):
    """(low, high) flow for one material, whole span (start+end).
    Returns (None, None) when no row for the material has a flow."""
    pool = [r for r in rows if _same_material(r.get("material"), material)]
    return flow_range(pool)


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
            # The material's own tested flow range, for the airflow
            # verdict below (doc Step 1 items 3 and 4).
            material_flow = material_flow_range(rows, material)
            # Fewer than 3 rows for a material means extrapolated,
            # not covered — but only on a real dataset (20+ rows).
            # The 6-row sample is explicitly a sample, so the rule
            # does not apply to it. The "coverage" key tells
            # build_answer to use the coverage sentence (not the
            # generic "both beyond" one, which would name an airflow
            # that was never given).
            if len(rows) >= 20:
                count = sum(1 for r in rows if _same_material(r.get("material"), material))
                if count < 3:
                    return {
                        "verdict": "BEYOND",
                        "reason": f"Only {count} {material} row(s) in the dataset — fewer than 3, so this is extrapolated, not covered.",
                        "unknown": [f"more {material} rows"],
                        "coverage": "too_few",
                    }
        else:
            return {
                "verdict": "BEYOND",
                "reason": f"No {material} rows in the dataset, so this cannot be classified from the data.",
                "unknown": [f"rows for {material}"],
                "coverage": "no_rows",
            }
    elif rows:
        o2_min, o2_max = dataset_range(rows)
        range_label = f"{o2_min}–{o2_max}% O2"
        material_flow = None
    else:
        o2_min, o2_max = DEFAULT_O2_MIN, DEFAULT_O2_MAX
        range_label = f"{o2_min}–{o2_max}% O2"
        material_flow = None

    unknown = []
    if airflow_cm_s is None:
        unknown.append("airflow_cm_s (not given for this question)")

    o2_far = oxygen_pct < o2_min - NEAR_POINTS or oxygen_pct > o2_max + NEAR_POINTS
    o2_outside = oxygen_pct < o2_min or oxygen_pct > o2_max
    # Airflow: each material's own tested flow range with a 25%
    # margin (doc Step 1 items 3 and 4). The margin is 25% of the
    # range width, on both sides (low side clamped at 0 — airflow
    # cannot be negative). No material, or a material with no flow
    # data, falls back to the BASS-II hardware band (0–55 cm/s,
    # NEAR up to 65).
    if airflow_cm_s is None:
        air_outside = False
        air_far = False
        flow_label = f"0–{AIRFLOW_MAX} cm/s"
    elif material_flow is not None and material_flow != (None, None):
        flow_low, flow_high = material_flow
        margin = FLOW_MARGIN * (flow_high - flow_low)
        near_low = max(0.0, flow_low - margin)
        near_high = flow_high + margin
        flow = float(airflow_cm_s)
        air_outside = flow < flow_low or flow > flow_high
        air_far = flow < near_low or flow > near_high
        flow_label = (
            f"{material} {flow_low}–{flow_high} cm/s (25% margin)"
        )
    else:
        flow = float(airflow_cm_s)
        air_outside = flow < 0 or flow > AIRFLOW_MAX
        air_far = flow > NEAR_AIRFLOW_MAX
        flow_label = f"0–{AIRFLOW_MAX} cm/s"

    if o2_far or air_far:
        verdict = "BEYOND"
        if o2_far and air_far:
            reason = (
                f"{oxygen_pct}% O2 and {airflow_cm_s} cm/s airflow are both "
                f"clearly outside the tested range ({range_label}, "
                f"{flow_label})."
            )
        elif o2_far:
            reason = (
                f"{oxygen_pct}% O2 is clearly outside the tested range "
                f"({range_label})."
            )
        else:
            reason = (
                f"{airflow_cm_s} cm/s airflow is clearly outside the tested "
                f"range ({flow_label})."
            )
    elif o2_outside or air_outside:
        verdict = "NEAR"
        if o2_outside and air_outside:
            reason = (
                f"{oxygen_pct}% O2 and {airflow_cm_s} cm/s airflow are both "
                f"just outside the tested range ({range_label}, "
                f"{flow_label})."
            )
        elif o2_outside:
            reason = (
                f"{oxygen_pct}% O2 is just outside the tested range "
                f"({range_label}); the closest tested rows are at the edge."
            )
        else:
            reason = (
                f"{airflow_cm_s} cm/s airflow is just outside the tested "
                f"range ({flow_label})."
            )
    else:
        verdict = "INSIDE"
        reason = (
            f"{oxygen_pct}% O2 is inside the tested range ({range_label})."
        )

    # Which dimension(s) drove the verdict, for the answer sentence:
    # build_answer's BEYOND/NEAR sentence must name the airflow when
    # the airflow (not the oxygen) is what is outside — otherwise it
    # says "20.0% oxygen is beyond what was tested" for a 45 cm/s
    # airflow question, which is false (20% is inside the O2 range).
    drivers = []
    if o2_far or o2_outside:
        drivers.append("oxygen")
    if air_far or air_outside:
        drivers.append("airflow")

    return {"verdict": verdict, "reason": reason, "unknown": unknown,
            "drivers": drivers}
