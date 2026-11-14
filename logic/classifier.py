# Written with SI assistance (Claude), reviewed by Paridhi Singh
"""Lane B classifier — INSIDE / NEAR / BEYOND what NASA tested.

Rules (draft, from Lane B starter Nov 13 — team to confirm):
- Tested O2 range (BASS-II / PSI-25): 13.6–22.2% (129 rows; 18 rows above 21%).
  The starter's INSIDE band is ~10–22.2%; we use the verified 13.6–22.2%
  for O2, and treat anything below 13.6% as NEAR only if it is just outside.
- Tested airflow: 0–~55 cm/s (report NASA/TM-20210011385; ~35 cm/s with
  two flow restrictors). Do NOT use "up to 40 cm/s" as the max.
- Airflow is often UNKNOWN in the sample: the PSI-25 CSV has Fan display
  only, no cm/s column. When airflow is None, classify on O2 only and
  say so plainly in the result — never guess a cm/s value.
"""

O2_MIN = 13.6
O2_MAX = 22.2
AIRFLOW_MAX = 55.0
NEAR_O2_MAX = 25.0
NEAR_AIRFLOW_MAX = 65.0


def classify(oxygen_pct, airflow_cm_s=None):
    """Return a dict with verdict, reason, and what is unknown.

    oxygen_pct: float, the O2 % being asked about (required).
    airflow_cm_s: float or None. None = not in the data yet.
    """
    if oxygen_pct is None:
        return {
            "verdict": "BEYOND",
            "reason": "No oxygen value was given, so there is nothing to compare with the tested range.",
            "unknown": ["oxygen_pct"],
        }

    unknown = []
    if airflow_cm_s is None:
        unknown.append("airflow_cm_s (CSV has Fan display only, no cm/s yet)")

    o2_outside = oxygen_pct < O2_MIN or oxygen_pct > O2_MAX
    o2_far = oxygen_pct < O2_MIN - 5 or oxygen_pct > NEAR_O2_MAX
    air_outside = airflow_cm_s is not None and (
        airflow_cm_s < 0 or airflow_cm_s > AIRFLOW_MAX
    )
    air_far = airflow_cm_s is not None and airflow_cm_s > NEAR_AIRFLOW_MAX

    if o2_far or air_far:
        verdict = "BEYOND"
        if o2_far and air_far:
            reason = (
                f"{oxygen_pct}% O2 and {airflow_cm_s} cm/s airflow are both "
                f"clearly outside the tested range ({O2_MIN}–{O2_MAX}% O2, "
                f"0–{AIRFLOW_MAX} cm/s, 129 BASS-II tests)."
            )
        elif o2_far:
            reason = (
                f"{oxygen_pct}% O2 is clearly outside the tested range "
                f"({O2_MIN}–{O2_MAX}% O2, 129 BASS-II tests)."
            )
        else:
            reason = (
                f"{airflow_cm_s} cm/s airflow is clearly above the tested maximum "
                f"of ~{AIRFLOW_MAX} cm/s (129 BASS-II tests)."
            )
    elif o2_outside or air_outside:
        verdict = "NEAR"
        if o2_outside and air_outside:
            reason = (
                f"{oxygen_pct}% O2 and {airflow_cm_s} cm/s airflow are both "
                f"just outside the tested range ({O2_MIN}–{O2_MAX}% O2, "
                f"0–{AIRFLOW_MAX} cm/s); the closest tested rows are at the edge."
            )
        elif o2_outside:
            reason = (
                f"{oxygen_pct}% O2 is just outside the tested range "
                f"({O2_MIN}–{O2_MAX}% O2); the closest tested rows are at the edge of that range."
            )
        else:
            reason = (
                f"{airflow_cm_s} cm/s airflow is just above the tested maximum "
                f"of ~{AIRFLOW_MAX} cm/s; the closest tested rows are at the edge of that range."
            )
    else:
        verdict = "INSIDE"
        reason = (
            f"{oxygen_pct}% O2 is inside the tested range "
            f"({O2_MIN}–{O2_MAX}% O2, 129 BASS-II tests)."
        )

    return {"verdict": verdict, "reason": reason, "unknown": unknown}
