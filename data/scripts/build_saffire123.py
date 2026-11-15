# Written with SI assistance (Claude), reviewed by <teammate name - fill in>.
# Saffire I-III rows from PSI-98, PSI-99, PSI-100 (the real CSVs). One row per flight test.
# Rules: nothing guessed. Missing oxygen or pressure stays null. Blank material cells are filled only where another source corroborates it, and the row says so.
# Saffire II "1-g" columns are ground comparison results; their test conditions are not stated, so they are kept as raw fields on the flight row, not as separate earth rows.
import os
DATA_DIR = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))  # scripts live in data/scripts/
import csv, json, re
D = DATA_DIR
R = f"{D}/raw"
def read(name):
    return [r for r in csv.reader(open(f"{R}/{name}", encoding="utf-8-sig", newline=""))]
num = lambda s: float(re.search(r"\d+(?:\.\d+)?", s).group()) if re.search(r"\d", s) else None
rows, review = [], []

def base(id_, src, material, shape, o2s, o2e, flow, direction, outcome, onote, cite, fnote, raw):
    return {"id": id_, "source": src, "source_type": "psi_table", "material": material, "shape": shape,
            "o2_start": o2s, "o2_end": o2e, "flow_start": flow, "flow_end": flow, "direction": direction,
            "outcome": outcome, "outcome_note": onote, "gravity": "micro", "pressure_kPa": None, "spread_rate": None,
            "sample_id": raw["raw_sample"], "flow_note": fnote, "flags": [], "citation": cite, **raw, "raw_group": src}
dirmap = lambda s: s.strip().lower() if s.strip().lower() in ("concurrent", "opposed") else "unknown"

# ---------------- PSI-98 (Saffire-1) ----------------
for r in read("PSI-98_Experimental_table_SAFFIRE-1.csv")[1:]:
    if not re.fullmatch(r"S\d+", r[0].strip()): continue
    rng = re.findall(r"\d+(?:\.\d+)?", r[6]); o2s = float(rng[0]); o2e = float(rng[1]) if len(rng) > 1 else None
    rows.append(base(f"PSI-98:{r[0].strip()}", "psi-98", "SIBAL",
        f"fabric, {r[3]} cm by {r[4]} cm as listed (length, width columns may be swapped; ICES-2021-266 Table 2 lists Saffire I SIBAL as 94 cm long, 41 cm wide)",
        o2s, o2e, num(r[5]), dirmap(r[10]), "unknown", "",
        f"NASA PSI-98 Saffire-1 experimental table, sample {r[0].strip()} (psi.nasa.gov, PSI-98)",
        f"PSI-98 gives burn time {r[9]} s but no statement of how the flame ended, so outcome is unknown. Oxygen printed as '{r[6]}'" + (" (a range, kept as start and end)." if o2e else " (approximate, ~)."),
        {"raw_sample": r[0].strip(), "raw_material": r[1], "raw_thickness": r[2] + " (header says cm; likely mm)", "raw_o2": r[6], "raw_air_display": r[5], "raw_burn_time_s": r[9], "raw_direction": r[10]}))

# ---------------- PSI-100 (Saffire-3) ----------------
for r in read("PSI-100_Experimental_table_SAFFIRE-3.csv")[1:]:
    if not re.fullmatch(r"S\d+", r[0].strip()): continue
    x = base(f"PSI-100:{r[0].strip()}", "psi-100", "SIBAL", f"fabric, {r[3].strip()} long, {r[4].strip()} wide, thickness '{r[2].strip()}' as printed",
        None, None, num(r[5]), dirmap(r[6]), "unknown", "",
        f"NASA PSI-100 Saffire-3 experimental table, sample {r[0].strip()} (psi.nasa.gov, PSI-100)",
        "PSI-100 gives no oxygen, pressure or outcome, so o2_start is null and the row is context_only (cannot be placed on the map)."
        + (" ICES-2021-266 Table 2 lists a Saffire III SIBAL test at 25 cm/s; PSI-100 says 30 cm/s. Not reconciled." if dirmap(r[6]) == "concurrent" else ""),
        {"raw_sample": r[0].strip(), "raw_material": r[1], "raw_thickness": r[2], "raw_air_display": r[5], "raw_direction": r[6]})
    x["flags"] = ["context_only"]
    rows.append(x)

# ---------------- PSI-99 (Saffire-2) ----------------
mat_above = None
NOTE4 = "The flames remain anchored at the base of the sample"
for r in read("PSI-99_Experimental_table_SAFFIRE-2.csv")[1:]:
    if not re.fullmatch(r"2-\d+", r[0].strip()): continue
    sid = r[0].strip(); material_cell = r[1].strip()
    o2 = [float(x) for x in re.findall(r"\d+\.\d+", r[6])]
    o2s, o2e = o2[0], (o2[1] if len(o2) > 1 else None)
    raw = {"raw_sample": sid, "raw_material": r[1], "raw_thickness": r[2], "raw_air_display": r[5], "raw_o2": r[6],
           "raw_ignition_power": r[7], "raw_ignition_time": r[8], "raw_burn_time": r[9], "raw_direction": r[10],
           "raw_ug_burn_length": r[11], "raw_ug_spread": r[12], "raw_1g_burn_length": r[13], "raw_1g_spread_rate": r[14]}
    d = dirmap(r[10]); cite = f"NASA PSI-99 Saffire-2 experimental table, sample {sid} (psi.nasa.gov, PSI-99)"
    approx = "Oxygen printed as '" + r[6] + "'" + (" (approximate, ~; derived from CO2 production, Note 1)." if "~" in r[6] else " (start and end values).")
    ground = f" Ground (1-g) comparison for this sample: burn length '{r[13]}', spread rate '{r[14]}'; its test conditions are not stated, so it is kept as raw fields, not as a separate row."
    note_ices = " ICES-2021-266 Table 2 lists Saffire II SIBAL tests II-5 and II-6 at 21% oxygen and 20 and 25 cm/s; PSI-99 lists ~22.1% and 20 cm/s. Not reconciled." if sid in ("2-5", "2-6") else ""
    if sid == "2-7":   # one sample card with two materials: split into two rows
        for mat, shape, onote, key in (("PMMA", "sheet, 0.85 mm thick, 5 cm long, 5 cm wide", "The PMMA portion was completely consumed", "PMMA"),
                                        ("Nomex", "fabric, 0.37 mm thick, 24 cm long, 5 cm wide", "the Nomex was not ignited", "Nomex")):
            outcome = "burning" if key == "PMMA" else "no_ignition"
            rows.append(base(f"PSI-99:2-7-{key}", "psi-99", mat, shape, o2s, o2e, num(r[5]), d, outcome, onote, cite + f" ({key} part, Note 2)",
                f"PSI-99 lists one row for 'PMMA & Nomex' (thickness '0.85 and 0.37 mm', length '5 and 24 cm'); split here in that order. " + approx + ground, dict(raw, raw_group_part=key)))
        continue
    if sid in ("2-1", "2-2", "2-3", "2-4"):
        mat, shape = "silicone", f"sheet, {r[2].strip()} thick" + (" ('037 mm' as printed, likely 0.37)" if r[2].strip().startswith("037") else "") + f", {r[3].strip()} long, {r[4].strip()} wide"
        outcome, onote = "no_ignition", "Insignificant"
        review.append({"id": f"PSI-99:{sid}", "cell_verbatim": "Burn Time: Insignificant; micro-g burn length: ~ 0", "decision": "no_ignition",
                       "why_judgement_call": "The table never says 'did not ignite'. Burn time 'Insignificant' and burn length ~0 mean no sustained burn; same convention as Zhao T9/T10/T28a."})
        fn = "Burn time 'Insignificant' and micro-g burn length '~ 0': no sustained burn. " + approx + ground
    elif sid in ("2-5", "2-6"):
        mat = "SIBAL"; shape = f"fabric, {r[2].strip()} thick" + (" ('037 mm' as printed, likely 0.37)" if r[2].strip().startswith("037") else "") + f", {r[3].strip()} long, {r[4].strip()} wide"
        outcome, onote = "burning", r[11].strip()
        fn = (f"Micro-g burn length {r[11]} equals the {r[3]} sample length, burn time {r[9]}. " + ("Material cell is blank in PSI-99; taken as the same as the row above (SIBAL), consistent with ICES-2021-266 Table 2. " if not material_cell else "")
              + approx + note_ices + ground)
    else:   # 2-8, 2-9 PMMA
        mat = "PMMA"; shape = f"slab, thickness '{r[2].strip()}', {r[3].strip()} long, {r[4].strip()} wide"
        outcome, onote = "burning", NOTE4
        fn = (f"Burn time {r[9]}; micro-g burn length {r[11]}. " + ("Material cell is blank in PSI-99; taken as PMMA (the ICES-2021-266 paper says Saffire II had two PMMA samples). " if not material_cell else "") + approx + ground)
    rows.append(base(f"PSI-99:{sid}", "psi-99", mat, shape, o2s, o2e, num(r[5]), d, outcome, onote, cite, fn, raw))

json.dump(rows, open(f"{D}/tests_saffire123.json", "w"), indent=1)
with open(f"{D}/review_saffire123.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(review[0].keys())); w.writeheader(); w.writerows(review)
print("rows:", len(rows), {s: sum(1 for x in rows if x['source'] == s) for s in ('psi-98', 'psi-99', 'psi-100')})
for x in rows: print(x["id"], x["material"], x["o2_start"], x["o2_end"], x["flow_start"], x["direction"], x["outcome"], x["flags"])
