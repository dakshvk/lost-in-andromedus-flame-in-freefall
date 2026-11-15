# Written with SI assistance (Claude), reviewed by <teammate name - fill in>.
# Lane A: builds data/tests.json (all 129 PSI-25 rows) from
#   - PSI-25 CSV (oxygen, flow text, material)
#   - Zhao et al. 2015 appendix (outcomes for the 27 SIBAL rows), data/zhao_appendix.json, verified against the PDF
#   - BASS-II report Appendix A notes (outcomes for the other 102 rows), data/bass2_appendixA_notes.json
# Rule: an outcome is set only from what the source text says. Anything judgement-based stays "unknown"
# and is listed in data/review_needed.csv with a proposed label for a human to confirm.
import os
DATA_DIR = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))  # scripts live in data/scripts/
import csv, json, re, random
from collections import Counter

D = DATA_DIR
rows = list(csv.reader(open(f"{D}/raw/PSI-25_Experimental table_BASS-II.csv", encoding="utf-8-sig", newline="")))[1:]
rows = [r for r in rows if any(c.strip() for c in r)]
(PI, TEST, DATE, GMT, SAMPLE, MAT, RESTR, FAN, AIR, RAD, FRAMES, O2I, O2F, CO2I, CO2F, COI, COF) = range(17)
notes = json.load(open(f"{D}/bass2_appendixA_notes.json"))
direction_raw = json.load(open(f"{D}/bass2_direction.json"))
zhao = json.load(open(f"{D}/zhao_appendix.json"))
ZHAO = {k: tuple(v) for k, v in zhao.items()}  # key -> (width, flow text, o2 text, comment|None)

OUTCOME_ZHAO = {"Quenched": "quenched", "No ignition": "no_ignition", "Reused, did not ignite": "no_ignition",
                "Blow-off": "blow_off", "No Blow-off": "burning", "Reused, one sided flame": "burning",
                "Reused, ignited": "ignited_only"}
ALLOWED = {"burning", "quenched", "blow_off", "no_ignition", "ignited_only", "unknown"}

# ---- labels for non-SIBAL rows, from the BASS-II Appendix A note text only ----
CLEAR = {}
for o, ids in {
    "quenched": "B9 B10 B11 B13 B16 B17 B21 B22 F4 M2 M3 M4 M5 M8 M9 M10 M11 M13 M14 M15 M18 M19 M20 O3a O4 O8a O13a O14 O15a O15b O19 P1 P3a P9 P10 P12 P13b P14 P16 P17 P18 P19 P20 P21a P22a P22b P23 P24 P25 T7",
    "blow_off": "B18 B19 O5a O7 O8b O9 O10 O11 O17",
    "no_ignition": "F1 F2 F3",   # report section 3.1: "The three Nomex samples did not ignite"
    "burning": "B6 B8 B15 B20 M6 M7 M16",
}.items():
    for t in ids.split(): CLEAR[t] = o
# note says nothing about what happened (colour, soot, hardware trouble, crew turned flow off) or row not in report
UNKNOWN = set("B1 B2 B3 B4 B5 B7 B12 M1 O1 M12 O2 O3b O6 P2 P3b P15 P21b O20 O21 O22".split())
REVIEW = {  # id: (proposed label, why it is a judgement call). Final outcome stays "unknown" until a human confirms.
    "B14": ("no_ignition", "Note: 'only brief ignition, flame extinguished'. It lit briefly, so not clearly 'did not light'."),
    "M17": ("burning", "30-min burn at constant flows, then crew turned the fan to 0 to extinguish. No quench or blow-off stated."),
    "P4": ("burning", "'long slow burn, steady ... until turned off flow': crew turned the flow off."),
    "P5": ("burning", "'flame persisted for all' flows; crew turned flow to 0 to extinguish."),
    "P6": ("burning", "'steady burning until turned flow off'."),
    "P13a": ("burning", "Flame persisted through the pot steps; went out when crew turned the pot to 0."),
    "O5b": ("no_ignition", "'Would not sustain a flame without igniter on'."),
    "O12": ("no_ignition", "'No sustained flame at any flow'; PSI-25 Air display also says 'no ign at any flow'."),
    "O16": ("no_ignition", "'Brief flame ... no joy on sustained flame'."),
    "P8": ("no_ignition", "'would not stay lit'."),
    "T3": ("no_ignition", "'Multiple ignition attempts ..., brief flames go out'."),
    "O13b": ("quenched", "'Only stayed lit at 0.9 for less than a minute': implies it went out but does not say so."),
    "O18": ("quenched or blow_off", "Stagnation region blew out, flame restabilized, later 'extinguished after multiple oscillations': mixed."),
}

# Decisions on the 13 judgement calls. Source: Claude's suggestion, accepted by the Lane A owner on 2026-11-14
# (not independently re-read by a second person yet). Basis: plan rule "label only what the note says";
# precedent: Zhao labels T9/T10 ("Brief ignition but flame extinguished...") and T28a ("only briefly flashed then went out") as no ignition.
DECISION = {"B14": "no_ignition", "O5b": "no_ignition", "O12": "no_ignition", "O16": "no_ignition", "P8": "no_ignition",
            "T3": "no_ignition", "M17": "unknown", "P4": "unknown", "P5": "unknown", "P6": "unknown", "P13a": "unknown",
            "O13b": "unknown", "O18": "quenched"}
assert set(DECISION) == set(REVIEW)

def num(s):
    s = s.strip()
    return float(s) if re.fullmatch(r"-?\d+(?:\.\d+)?", s) else None
def clean(x):
    return None if x is None else (int(x) if float(x).is_integer() else x)

def group(name):
    n = name.lower()
    if "sibal" in n: return "SIBAL"
    if "nomex" in n: return "Nomex"
    if "wax" in n: return "wax"
    return "PMMA"

def shape_of(tid, raw, grp):
    n = raw.lower()
    if grp == "SIBAL":
        w = re.search(r"(\d+)\s*cm", raw)
        return f"flat fabric, {w.group(1)} cm wide" if w else "unknown"
    if grp == "Nomex": return "unknown"
    if grp == "wax": return "candle"
    if "spherical" in n: return "spherical section, 4 cm"
    if "rod" in n:
        s = re.search(r"(\d+/\d+|0\.5)", raw); c = "black" if "blac" in n else ("clear" if "clear" in n else "")
        return ("rod, " + (s.group(1) + " inch " if s else "") + c).strip()
    if tid.startswith("B"): return "film"
    if tid.startswith("M"): return "slab" if "slab" in n else "sheet"
    return "unknown"

FLOW_OVERRIDE = {  # hand notes where Air display has text (all flagged in flow_note, never silent)
    "T6": (5, None, "Air display '5 2 1 <1' ends in '<1' (less than 1, exact value not given), so flow_end is left empty"),
    "T21": (11, 47, "Air display '11 max(47)': 47 is in brackets after 'max'"),
    "O5b": (5, None, "Air display '49 5 cm/s': 49 is the fan reading, 5 cm/s is the flow (pot 1.3 = 5 cm/s, 2 restrictors cap flow near 35 cm/s). Fixed after team check 2026-11-14"),
    "O13a": (5, 0, "Air display '49 44 42 41 41 40.5 (5 2 0)': the first numbers are fan readings; bracket gives flow 5, 2, 0 cm/s, so flow falls from 5 to 0. Fixed after team check 2026-11-14"),
    "T29": (5, 2, "Air display '5 2(?)': the source itself marks the last value 2 with (?)"),
}
def parse_flow(raw, tid):
    if tid in FLOW_OVERRIDE: return FLOW_OVERRIDE[tid]
    raw = raw.strip()
    if not raw: return None, None, "Air display blank in PSI-25; any flow text is in Fan display (fan setting, not converted)"
    if raw.lower().startswith("see"): return None, None, f"Air display says '{raw}'; flow text is in Fan display (fan setting, not converted)"
    nums = [float(x) for x in re.findall(r"\d+(?:\.\d+)?", raw)]
    if not nums: return None, None, f"Air display has no number ({raw!r})"
    if re.fullmatch(r"[\d.\s]+(low)?\s*", raw):   # plain numbers, optionally ending in the word 'low'
        n = ""
        if nums[0] == 0: n = "Air display reads 0 as recorded; see outcome_note"
        if len(nums) > 2 and max(nums) > max(nums[0], nums[-1]):
            n = (n + "; " if n else "") + f"flow went up to {clean(max(nums))} in between"
        return clean(nums[0]), clean(nums[-1]), n
    first = clean(nums[0]) if re.match(r"\s*\d", raw) else None
    return first, None, f"Air display has text or bracketed numbers ({raw!r}); flow_end left empty, original kept in raw_air_display"

out, review_rows = [], []
for r in rows:
    tid, gmt = r[TEST], r[GMT]
    grp = group(r[MAT])
    key = f"GMT{gmt}-{tid}"
    fs, fe, fnote = parse_flow(r[AIR], tid)
    o2e = num(r[O2F]); o2s = num(r[O2I]); assert o2s is not None, tid
    rn = notes.get(tid, {})
    report_note = rn.get("note", "")
    flags = []
    if o2e is not None and not (10 <= o2e <= 23): flags.append("o2_end_suspect")
    outcome, onote = "unknown", ""
    if grp == "SIBAL":
        width, zflow, zo2, comment = ZHAO[key]
        assert abs(float(zo2.strip("*")) - o2s) < 1e-9, key
        if key in ("GMT45-T1", "GMT45-T2"): flags.append("o2_reading_questioned")
        zn = f"Zhao appendix gives {zflow} cm/s"
        fnote = ("raw Air display: 11 max(47); " + zn + " (confirms 47)") if tid == "T21" else ((fnote + "; " if fnote else "") + zn)
        if comment:
            outcome, onote = OUTCOME_ZHAO[comment], comment; flags.append("outcome_from_zhao")
        citation = f"Zhao et al. 2015, NASA 20150008962, Appendix, {key}; oxygen and flow from PSI-25 test {tid}"
        direction = "concurrent"   # Zhao appendix title: flat SIBAL fabrics in concurrent flow
    else:
        if tid in CLEAR: outcome = CLEAR[tid]
        elif tid in REVIEW:
            outcome = DECISION[tid]
            review_rows.append({"id": f"PSI-25:{key}", "test": tid, "material_raw": r[MAT], "report_note_verbatim": report_note,
                                "proposed_outcome": REVIEW[tid][0], "why_judgement_call": REVIEW[tid][1],
                                "FINAL_outcome_used": outcome})
        else: assert tid in UNKNOWN, f"unlabeled {tid}"
        if report_note:
            onote = report_note; flags.append("outcome_from_report_notes")
            citation = f"BASS-II report NASA/TM-20210011385, Appendix A, test {tid}, GMT {rn.get('gmt') or gmt}; oxygen and flow from PSI-25"
        else:
            fnote = (fnote + "; " if fnote else "") + "no entry for this test in BASS-II Appendix A"
            citation = f"PSI-25 BASS-II table, test {tid}, GMT {gmt} (psi.nasa.gov/physci/repo, PSI-25); not listed in BASS-II report Appendix A"
        d = direction_raw.get(tid)
        direction = {"Opposed": "opposed", "Concurrent": "concurrent"}.get(d, "unknown")
    if "o2_end_suspect" in flags:
        fnote = (fnote + "; " if fnote else "") + f"final O2 {r[O2F]} is outside 10-23%, kept, map uses o2_start"
    assert outcome in ALLOWED
    shape = shape_of(tid, r[MAT], grp)
    if key == "GMT190-T24":  # sources disagree on width: record, do not choose
        shape = "flat fabric, 1 cm wide (PSI-25 and BASS-II report); Zhao appendix lists 2.2 cm"
    out.append({
        "id": f"PSI-25:{key}", "source": "psi-25", "source_type": "psi_table", "material": grp,
        "shape": shape, "o2_start": o2s, "o2_end": o2e, "flow_start": fs, "flow_end": fe,
        "direction": direction, "outcome": outcome, "outcome_note": onote, "gravity": "micro", "pressure_kPa": None,
        "spread_rate": None, "sample_id": r[SAMPLE], "flow_note": fnote, "flags": flags, "citation": citation,
        "raw_date": r[DATE], "raw_material": r[MAT], "raw_air_display": r[AIR], "raw_fan_display": r[FAN],
        "raw_flow_restrictor": r[RESTR], "raw_o2_end": r[O2F], "raw_direction_report": direction_raw.get(tid),
        "raw_gmt_report": rn.get("gmt"), "raw_report_note": report_note, "raw_group": ("PMMA rod" if grp == "PMMA" and "rod" in r[MAT].lower() else ("PMMA other" if grp == "PMMA" else grp)),
    })

paper = (json.load(open(f"{D}/tests_saffire45.json")) + json.load(open(f"{D}/tests_link2018.json"))
         + json.load(open(f"{D}/tests_saffire123.json")))   # Saffire IV/V, Link 2018, Saffire I-III
assert not ({p["id"] for p in paper} & {o["id"] for o in out}), "duplicate ids"
LOW_FLOW_CM_S = 2   # team choice (Daksh, 2026-11-14): report says low flows have "high error bars" but gives no number
for _r in out + paper:
    _f = [v for v in (_r.get("flow_start"), _r.get("flow_end")) if v is not None]
    if _f and min(_f) < LOW_FLOW_CM_S and "low_flow_uncertain" not in _r["flags"]:
        _r["flags"].append("low_flow_uncertain")
json.dump(out + paper, open(f"{D}/tests.json", "w"), indent=1)   # PSI-25 checks below use `out` only
with open(f"{D}/review_needed.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(review_rows[0].keys()) + ["human_decision (fill in)"]); w.writeheader()
    for x in review_rows: w.writerow({**x, "human_decision (fill in)": "default: Claude suggestion accepted by Lane A owner, 2026-11-14; second-person check pending"})

# blind relabel sample for the second-person check (note text only, no label)
random.seed(14)
labeled = [o for o in out if o["source"] == "psi-25" and o["material"] != "SIBAL" and o["outcome"] != "unknown"]
pick = random.sample(labeled, 20)
with open(f"{D}/blind_check_20.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["id", "report_note_verbatim", "your_label (quenched/blow_off/no_ignition/burning/unknown)"])
    for o in pick: w.writerow([o["id"], o["raw_report_note"], ""])
with open(f"{D}/blind_check_20_KEY.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["id", "lane_a_label"])
    for o in pick: w.writerow([o["id"], o["outcome"]])

# ---- checks ----
print("rows:", len(out), "(expected 129)")
print("groups:", dict(Counter(o["raw_group"] for o in out)), "(expected SIBAL 27, PMMA rod 54, PMMA other 44, Nomex 3, wax 1)")
sib = Counter(o["outcome"] for o in out if o["material"] == "SIBAL")
print("SIBAL outcomes:", dict(sib), "(expected quenched 6, no_ignition 6, blow_off 1, burning 3, ignited_only 4, unknown 7)")
assert dict(sib) == {"quenched": 6, "no_ignition": 6, "blow_off": 1, "burning": 3, "ignited_only": 4, "unknown": 7}
oth = Counter(o["outcome"] for o in out if o["material"] != "SIBAL")
print("non-SIBAL outcomes:", dict(oth), "| review needed:", len(review_rows))
print("all have citation:", all(o["citation"] for o in out), "| all outcomes allowed:", all(o["outcome"] in ALLOWED for o in out),
      "| o2_start null:", sum(o["o2_start"] is None for o in out))
print("o2_end_suspect:", [o["id"].split("-")[-1] for o in out if "o2_end_suspect" in o["flags"]])
print("report GMT differs from PSI-25:", [(o["id"], o["raw_gmt_report"]) for o in out if o["raw_gmt_report"] and not o["id"].startswith(f"PSI-25:GMT{o['raw_gmt_report']}-")])
