# PSI-26 (BASS) and PSI-20 (ACME BRE) rows. Both are context_only: PSI-26 has no oxygen or airflow, PSI-20 is a gas burner day-summary.
# Written to tests_context_only.json, NOT merged into tests.json (psi-26 is not an allowed source in the contract and the freeze has passed).
import os
DATA_DIR = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))  # scripts live in data/scripts/
import csv, json, re
D = DATA_DIR; R = f"{D}/raw"
rows = []
# ---------- PSI-26 ----------
rd = list(csv.reader(open(f"{R}/PSI-26_Experimental_table_BASS.csv", encoding="utf-8-sig", newline="")))[1:]
rd = [r for r in rd if any(c.strip() for c in r)]
assert len(rd) == 122, len(rd)
samples_text = {}
for r in rd: samples_text.setdefault(r[4].strip(), []).append(r[5].lower())
def material(txt, sample):
    t = txt.lower()
    if "sibal" in t: return "SIBAL", ""
    if "nomex" in t: return "Nomex", ""
    if "wax" in t or "candle" in t: return "wax", ""
    if "ultem" in t: return "other", "Ultem (not one of the five material cards)"
    if "pmma" in t: return "PMMA", ""
    if "sphere" in t:   # material not written in this cell
        if any("pmma" in x for x in samples_text[sample]):
            return "PMMA", f"material not written in this cell; PMMA taken from another row of the same sample # {sample}"
        return "other", "material not stated for this sample in the PSI-26 table (cell says only the shape), so not assumed"
    return "other", "material not stated"
seen = set(); n26 = 0
for r in rd:
    date, gmt, asrun, test, samp, mat = [c.strip() for c in r]
    if not test and not asrun:      # 8/3/2012 "SOOT Cleaning": not a burn test
        continue
    m, mnote = material(mat, samp)
    rid = f"PSI-26:GMT{gmt}-T{test}"
    assert rid not in seen, rid; seen.add(rid)
    dirn = "opposed" if "opposed" in mat.lower() or "oppsed" in mat.lower() else "unknown"
    notes = ["PSI-26 table has no oxygen, airflow or outcome columns, so the row cannot be placed on the map."]
    if mnote: notes.append(mnote)
    if re.search(r"\d/\d+/(2103|`12)", date) or "`" in date or "2103" in date: notes.append(f"date printed '{date}' looks like a typo; kept as printed")
    rows.append({"id": rid, "source": "psi-26", "source_type": "psi_table", "material": m, "shape": mat.strip(), "o2_start": None, "o2_end": None,
        "flow_start": None, "flow_end": None, "direction": dirn, "outcome": "unknown", "outcome_note": "", "gravity": "micro", "pressure_kPa": None,
        "spread_rate": None, "sample_id": samp, "flow_note": " ".join(notes), "flags": ["context_only"],
        "citation": f"NASA PSI-26 BASS experimental table, GMT {gmt} test {test} (psi.nasa.gov, PSI-26)",
        "raw_date": date, "raw_gmt": gmt, "raw_as_run_test": asrun, "raw_test": test, "raw_sample": samp, "raw_material": mat, "raw_group": "psi-26"})
    n26 += 1
# ---------- PSI-20 ----------
rd20 = list(csv.reader(open(f"{R}/PSI-20_Experimental_table_ACME_BRE.csv", encoding="utf-8-sig", newline="")))[1:]
rd20 = [r for r in rd20 if any(c.strip() for c in r)]
assert len(rd20) == 18, len(rd20)
for i, r in enumerate(rd20, 1):
    y, mo, d, burner, fuel, o2, ign, note = [c.strip() for c in r]
    extra = " Printed oxygen '%s' has a percent sign and is probably a typo; kept as printed." % o2 if "%" in o2 else ""
    rows.append({"id": f"PSI-20:{y}{mo}{d}-{i}", "source": "psi-20", "source_type": "psi_table", "material": "other",
        "shape": f"porous circular gas burner, {burner} mm diameter, fuel {fuel} (a burner that imitates a burning solid, not a solid sample)",
        "o2_start": None, "o2_end": None, "flow_start": None, "flow_end": None, "direction": "unknown", "outcome": "unknown", "outcome_note": "",
        "gravity": "micro", "pressure_kPa": None, "spread_rate": None, "sample_id": f"{y}-{mo}-{d}",
        "flow_note": f"Day summary row: {ign} flames ignited that day, at oxygen values listed as '{o2}'. Pressures were varied but are not listed in the table. Not a single burn, so no outcome or oxygen value is set." + extra,
        "flags": ["context_only"], "citation": f"NASA PSI-20 ACME BRE experimental table, row {i}, {y} {mo} {d} (psi.nasa.gov, PSI-20)",
        "raw_year": y, "raw_month": mo, "raw_date": d, "raw_burner_mm": burner, "raw_fuel": fuel, "raw_o2": o2, "raw_flames_ignited": ign, "raw_notes": note, "raw_group": "psi-20"})
tests = json.load(open(f"{D}/tests.json"))
assert not ({x["id"] for x in rows} & {x["id"] for x in tests}), "id clash"
assert len({x["id"] for x in rows}) == len(rows)
json.dump(rows, open(f"{D}/tests_context_only.json", "w"), indent=1)
import collections
print("PSI-26 rows:", n26, "(122 table lines minus 1 'SOOT Cleaning' line); PSI-20 rows:", len(rd20))
print(collections.Counter(x["material"] for x in rows if x["source"] == "psi-26"))
print([x["id"] for x in rows if x["material"] == "other" and x["source"] == "psi-26"])
