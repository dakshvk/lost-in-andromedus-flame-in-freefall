# Written with SI assistance (Claude), reviewed by <teammate name - fill in>.
# Lane A, Steps 1-2 (draft): checks PSI-25 against the plan's counts, builds the 27 SIBAL rows
# (outcomes NOT yet joined: waiting for the Zhao appendix), writes manifest + column map.
import os
DATA_DIR = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))  # scripts live in data/scripts/
import csv, json, re, hashlib, os, sys
from collections import Counter

DATA = DATA_DIR
RAW = f"{DATA}/raw/PSI-25_Experimental table_BASS-II.csv"
NUM = re.compile(r"\d+(?:\.\d+)?")

def num(s):
    s = s.strip()
    return float(s) if re.fullmatch(r"-?\d+(?:\.\d+)?", s) else None

def clean(x):
    if x is None: return None
    return int(x) if float(x).is_integer() else x

with open(RAW, newline="", encoding="utf-8-sig") as f:
    reader = csv.reader(f)
    header = next(reader)
    rows = [r for r in reader if any(c.strip() for c in r)]

assert len(header) == 17, f"expected 17 columns, got {len(header)}"
assert all(len(r) == 17 for r in rows), "a row does not have 17 fields"
H = {i: h.strip() for i, h in enumerate(header)}
(PI, TEST, DATE, GMT, SAMPLE, MAT, RESTR, FAN, AIR, RAD, FRAMES,
 O2I, O2F, CO2I, CO2F, COI, COF) = range(17)

def material_group(name):
    n = name.lower()
    if "sibal" in n: return "SIBAL"
    if "nomex" in n: return "Nomex"
    if "wax" in n: return "wax"
    if "rod" in n: return "PMMA rod"
    return "PMMA other"

# ---------- checks against the plan ----------
print("PSI-25 rows:", len(rows), "(expected 129); columns:", len(header), "(expected 17)")
cnt = Counter(material_group(r[MAT]) for r in rows)
print("Materials:", dict(cnt), "(expected SIBAL 27, rods 54, other PMMA 44, Nomex 3, wax 1)")
o2s = [num(r[O2I]) for r in rows]
print("o2_start missing:", sum(v is None for v in o2s), "| min", min(v for v in o2s if v is not None),
      "max", max(v for v in o2s if v is not None), "| rows above 21.0:", sum(v > 21.0 for v in o2s if v is not None), "(expected 18, max 22.2)")
plain = [r[TEST] for r in rows if num(r[AIR]) is not None]
blank = [r[TEST] for r in rows if not r[AIR].strip()]
print("Air display plain numbers:", len(plain), "(expected 25) | text:", len(rows) - len(plain), "(expected 104) | blank:", blank, "(expected O7,O8a,O8b,O9)")
susp = [r[TEST] for r in rows if (num(r[O2F]) is not None and not (10 <= num(r[O2F]) <= 23))]
print("Final O2 outside 10-23:", susp, "(expected B2,P22a,P22b,T28a,T28b)")
odd = sorted({r[DATE] for r in rows if not r[DATE].endswith("/2014")})
print("Dates not in 2014:", odd)
ids = [f"GMT{r[GMT]}-{r[TEST]}" for r in rows]
print("Unique GMT-Test ids:", len(set(ids)) == len(ids))

# ---------- SIBAL draft rows ----------
# Hand overrides where Air display has text. Each is flagged in flow_note, never silent.
FLOW_OVERRIDE = {
    "T6":  (5, None, "Air display '5 2 1 <1' ends in '<1' (less than 1, exact value not given), so flow_end is left empty"),
    "T21": (11, 47, "Air display '11 max(47)': 47 is in brackets after 'max'. The team's example row uses 47; confirm against the BASS-II report"),
    "T29": (5, 2, "Air display '5 2(?)': the source itself marks the last value 2 with (?)"),
}

def parse_flow(raw, tid):
    if tid in FLOW_OVERRIDE: return FLOW_OVERRIDE[tid]
    raw = raw.strip()
    if not raw: return None, None, "Air display blank in PSI-25"
    nums = [float(x) for x in NUM.findall(raw)]
    if re.fullmatch(r"[\d.\s]+", raw):
        return clean(nums[0]), clean(nums[-1]), ""
    return clean(nums[0]), None, f"Air display has text ('{raw}'); flow_end left empty"

sibal = []
for r in rows:
    if material_group(r[MAT]) != "SIBAL": continue
    tid, gmt = r[TEST], r[GMT]
    fs, fe, fnote = parse_flow(r[AIR], tid)
    o2e = num(r[O2F])
    width = re.search(r"(\d+)\s*cm", r[MAT])
    flags = []
    if o2e is not None and not (10 <= o2e <= 23): flags.append("o2_end_suspect")
    if (gmt, tid) in {("45", "T1"), ("45", "T2")}: flags.append("o2_reading_questioned")
    note = fnote
    if "o2_end_suspect" in flags:
        note = (note + "; " if note else "") + f"final O2 {r[O2F]} is outside 10-23%, kept, map uses o2_start"
    sibal.append({
        "id": f"PSI-25:GMT{gmt}-{tid}",
        "source": "psi-25", "source_type": "psi_table",
        "material": "SIBAL",
        "shape": f"flat fabric, {width.group(1)} cm wide" if width else "unknown",
        "o2_start": num(r[O2I]), "o2_end": o2e,
        "flow_start": fs, "flow_end": fe,
        "direction": "concurrent",  # Zhao 2015 abstract: SIBAL tested in concurrent forced flow
        "outcome": "unknown", "outcome_note": "",
        "gravity": "micro", "pressure_kPa": None,
        "spread_rate": None, "sample_id": r[SAMPLE],
        "flow_note": note,
        "flags": flags,
        "citation": f"PSI-25 BASS-II table, test {tid}, GMT {gmt} (psi.nasa.gov/physci/repo, PSI-25). Outcome: DRAFT, Zhao appendix not joined yet",
        "raw_date": r[DATE], "raw_material": r[MAT], "raw_air_display": r[AIR],
        "raw_fan_display": r[FAN], "raw_flow_restrictor": r[RESTR],
        "raw_o2_end": r[O2F],
    })
# ---------- Zhao appendix join (key = GMT + Test #) ----------
# Transcribed from NTRS 20150008962 Appendix (read via a text extraction of the PDF).
# HUMAN CHECK STILL NEEDED: compare comments/flows with the PDF page itself.
# key: (width_cm, zhao_flow_text, zhao_o2_text, comment or None)
ZHAO = {
 "GMT45-T1":(2.2,"10","18.5*",None), "GMT45-T2":(2.2,"10 to 5","18.5*",None),
 "GMT45-T4":(2.2,"10 to 2.2","18.7","Quenched"), "GMT45-T15":(2.2,"10 to 29","18.7","No Blow-off"),
 "GMT100-T5":(2.2,"10 to 2.4","18.8",None), "GMT100-T6":(2.2,"4.5 to 2.6","18.8",None),
 "GMT100-T13":(2.2,"4 to 2.2","17.5","Quenched"), "GMT100-T16":(2.2,"4 to 3","17.6",None),
 "GMT175-T9":(2.2,"10","16.4","No ignition"), "GMT175-T10":(2.2,"5","16.4","No ignition"),
 "GMT175-T18":(2.2,"5 to 2.6","17.4","Quenched"),
 "GMT178-T11":(2.2,"4","17.1",None), "GMT178-T12":(2.2,"5","16.8","No ignition"),
 "GMT178-T14":(2.2,"4 to 2.8","16.9","Quenched"), "GMT178-T17":(2.2,"6 to 53","16.9","No Blow-off"),
 "GMT190-T19":(1.2,"11","17.2",None), "GMT190-T20":(1.2,"11 to 3","17.2","Quenched"),
 "GMT190-T21":(1.2,"11 to 47","17.2","Blow-off"), "GMT190-T22":(1.2,"10.5 to 5","17.1","Quenched"),
 "GMT190-T23":(2.2,"10","17.2","Reused, did not ignite"), "GMT190-T24":(2.2,"10","18.2","Reused, one sided flame"),
 "GMT216-T25":(2.2,"5 to 2.5","20.8","Reused, ignited"), "GMT216-T26":(2.2,"5 to 2.5","20.8","Reused, ignited"),
 "GMT216-T27":(1.2,"5 to 2","20.7","Reused, ignited"), "GMT216-T28a":(1.2,"5","20.7","Reused, did not ignite"),
 "GMT216-T28b":(1.2,"5","20.7","Reused, did not ignite"), "GMT216-T29":(1.2,"5 to 2","20.7","Reused, ignited"),
}
OUTCOME_MAP = {"Quenched":"quenched","No ignition":"no_ignition","Reused, did not ignite":"no_ignition",
               "Blow-off":"blow_off","No Blow-off":"burning","Reused, one sided flame":"burning",
               "Reused, ignited":"ignited_only"}
keys_psi = {s["id"].split(":")[1] for s in sibal}
assert keys_psi == set(ZHAO), f"join keys differ: only-PSI {keys_psi-set(ZHAO)}, only-Zhao {set(ZHAO)-keys_psi}"
for s in sibal:
    key = s["id"].split(":")[1]
    width, zflow, zo2, comment = ZHAO[key]
    if abs(float(zo2.strip('*')) - s["o2_start"]) > 1e-9:
        print("O2 MISMATCH", key, zo2, s["o2_start"])
    zn = f"Zhao appendix gives {zflow} cm/s"
    if key == "GMT190-T21":  # Zhao confirms the 47 read from the bracket
        s["flow_note"] = "raw Air display: 11 max(47); " + zn + " (confirms 47)"
    else:
        s["flow_note"] = (s["flow_note"] + "; " if s["flow_note"] else "") + zn
    if comment:
        s["outcome"] = OUTCOME_MAP[comment]; s["outcome_note"] = comment
        s["flags"].append("outcome_from_zhao")
    s["citation"] = f"Zhao et al. 2015, NASA 20150008962, Appendix, {key}; oxygen and flow from PSI-25 test {s['id'].split('-')[-1]}"

oc = Counter(s["outcome"] for s in sibal)
print("SIBAL joined to Zhao appendix:", len(sibal), "of 27")
print("SIBAL outcomes:", dict(oc))
notes = Counter(s["outcome_note"] for s in sibal)
exp = {"quenched":6,"no_ignition":6,"blow_off":1,"burning":3,"ignited_only":4,"unknown":7}
assert dict(oc) == exp, f"outcome counts differ from acceptance check: {dict(oc)}"
assert notes["Reused, did not ignite"] == 3 and notes["No Blow-off"] == 2 and notes["Reused, one sided flame"] == 1
assert sum(1 for s in sibal if s["outcome_note"] in ("No ignition",)) == 3
print("ACCEPTANCE OK: quenched 6, no_ignition 6 (3 fresh + 3 reused), blow_off 1, burning 3 (2 'No Blow-off' + 1 one-sided), ignited_only 4, unknown 7")
print("SIBAL rows built:", len(sibal), "(expected 27)")

with open(f"{DATA}/tests.json", "w") as f:
    json.dump(sibal, f, indent=1)

# checklist the human matches against the Zhao table
with open(f"{DATA}/sibal_to_match.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["zhao_key", "psi25_o2_start", "psi25_air_display", "zhao_comment_VERBATIM (fill in)", "zhao_oxygen (check)", "zhao_flow (check)", "outcome (fill in)"])
    for s in sibal:
        k = s["id"].split(":")[1]
        w.writerow([k, s["o2_start"], s["raw_air_display"], ZHAO[k][3] or "(no comment)", ZHAO[k][2], ZHAO[k][1], s["outcome"]])

# manifest
sha = hashlib.sha256(open(RAW, "rb").read()).hexdigest()
manifest = {"files": [{
    "file": "data/raw/PSI-25_Experimental table_BASS-II.csv",
    "source": "NASA PSI-25 (BASS-II)",
    "url": "https://psi.nasa.gov/geode-py/ws/studies/PSI-25/download?file=PSI-25_Experimental%20table_BASS-II.csv&version=1&redirect=true",
    "obtained_via": "team repo, commit 29d142d (per Paridhi); not downloaded by this script",
    "download_time": None, "sha256": sha}],
    "si_note": "Written with SI assistance (Claude); to be reviewed by the team."}
json.dump(manifest, open(f"{DATA}/manifest.json", "w"), indent=1)
print("sha256:", sha)

# column map
cm = """# PSI-25 column map (SI note: written with SI assistance (Claude), reviewed by <name>)
Read from the actual file header, 17 columns.
| # | PSI-25 column | Feeds contract field |
|---|---|---|
""" + "\n".join(f"| {i+1} | {H[i]} | " + {
    PI: "not plotted (raw_pi)", TEST: "id (with GMT); join key to Zhao", DATE: "raw_date only, do not rely on it",
    GMT: "id (with Test #); join key to Zhao", SAMPLE: "sample_id", MAT: "material + shape (original in raw_material)",
    RESTR: "not plotted (raw_flow_restrictor)", FAN: "not plotted (raw_fan_display); fan setting, not cm/s",
    AIR: "flow_start / flow_end (original in raw_air_display); this is the cm/s column",
    RAD: "not plotted", FRAMES: "not plotted", O2I: "o2_start", O2F: "o2_end",
    CO2I: "not plotted (raw)", CO2F: "not plotted (raw)", COI: "not plotted (raw)", COF: "not plotted (raw)"}[i] + " |" for i in range(17))
open(f"{DATA}/column_map.md", "w").write(cm + "\n")
