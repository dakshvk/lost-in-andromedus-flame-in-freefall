# Written with SI assistance (Claude), reviewed by <teammate name - fill in>.
# Link et al. 2018 (Sci. Reports, DOI 10.1038/s41598-017-18398-4), Supplementary Table S1: 52 rows, 19 PMMA rod samples.
# Double entry (no second person available, so two independent reads by the same assistant):
#   A) script reads the PDF's table cells (pdfplumber) and forward-fills the merged cells
#   B) values typed by hand from the page-1 image, with cell borders visible
# They are compared; any difference stops the build.
import os
DATA_DIR = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))  # scripts live in data/scripts/
import json, pdfplumber

PDF = "/tmp/link/l.pdf"
D = DATA_DIR

# ---------- entry A ----------
tab = pdfplumber.open(PDF).pages[0].extract_tables()[0][1:]   # drop header row
A = []
for half, (c0, label) in enumerate([(0, "left"), (6, "right")]):
    d = o2 = samp = None
    for row in tab:
        cells = row[c0:c0 + 6]
        if cells[0]: d = cells[0]
        if cells[1]: o2 = cells[1]
        if cells[2]: samp = cells[2]
        if cells[3] is None: continue
        A.append((half, samp, float(d), float(o2), float(cells[3]), int(cells[4]), float(cells[5])))

# ---------- entry B (hand typed from the image) ----------
RAW = [
 # (sample, d_cm, O2, [(Vg, dt, Vf), ...], half)
 ("B13a", 1.27, 20.7, [(1.64,184,5.23),(1.54,232,5.27),(1.43,239,4.63),(1.38,238,4.69)], 0),
 ("B13b", 1.27, 20.6, [(1.64,159,7.09),(1.54,179,4.91)], 0),
 ("B5",   1.27, 19.3, [(1.64,192,3.76),(1.54,241,3.74)], 0),
 ("B9",   1.27, 17.6, [(1.64,147,4.57),(1.54,76,3.34),(1.43,154,2.67),(1.38,112,2.03)], 0),
 ("C25",  0.95, 20.9, [(1.58,115,6.09),(1.52,169,5.50),(1.48,181,5.59)], 0),
 ("B22",  0.95, 20.8, [(1.58,123,6.45),(1.58,79,8.31),(1.52,120,5.89),(1.48,146,4.10)], 0),
 ("B4",   0.95, 18.5, [(2.00,177,3.25),(1.87,131,3.10),(1.73,145,2.69)], 0),
 ("B12",  0.95, 17.5, [(1.01,121,3.08),(0.82,134,3.45),(0.60,129,3.65),(0.48,158,2.37)], 0),
 ("B6",   0.64, 18.9, [(2.00,90,10.00),(1.87,121,9.74),(1.73,93,8.32)], 1),
 ("B15",  0.64, 18.4, [(2.14,424,7.16)], 1),
 ("B14",  0.64, 18.4, [(1.98,384,6.38)], 1),
 ("B16",  0.64, 18.2, [(7.55,72,6.78),(1.67,139,7.62),(0.83,198,6.99),(0.72,170,5.68)], 1),
 ("B1",   0.64, 17.7, [(4.00,794,7.15),(2.15,23,5.91)], 1),
 ("C3a",  0.64, 17.7, [(2.50,33,8.37),(2.00,30,6.42)], 1),
 ("B19",  0.64, 17.5, [(7.55,67,4.69),(1.67,128,6.52),(0.83,189,6.25),(0.72,200,5.44)], 1),
 ("B2",   0.64, 17.4, [(2.50,24,7.25),(2.00,28,7.87)], 1),
 ("C3b",  0.64, 17.4, [(1.85,109,6.00)], 1),
 ("B10",  0.64, 17.0, [(2.00,106,5.41),(1.87,104,5.15),(1.73,148,4.22)], 1),
 ("P17",  0.64, 16.8, [(1.01,123,4.12),(0.82,187,4.78),(0.41,65,2.26)], 1),
]
B = [(half, s, d, o2, vg, dt, vf) for (s, d, o2, steps, half) in RAW for (vg, dt, vf) in steps]

print("rows: entry A =", len(A), "| entry B =", len(B), "(expected 52); samples:", len({r[1] for r in A}), "(expected 19)")
diffs = [(i, a, b) for i, (a, b) in enumerate(zip(A, B)) if a != b]
print("differences between entry A and entry B:", diffs if diffs else "none")
assert len(A) == len(B) == 52 and not diffs
o2s = [r[3] for r in A]; vgs = [r[4] for r in A]
print("sanity: O2 range", min(o2s), "to", max(o2s), "(plan: 16.8 to 20.9) | flow range", min(vgs), "to", max(vgs), "(plan: 0.41 to 7.55)")
assert (min(o2s), max(o2s), min(vgs), max(vgs)) == (16.8, 20.9, 0.41, 7.55)

COLOR = lambda s: "black" if s.startswith("B") else ("clear" if s.startswith("C") else "color not stated in Table S1")
HDR = {0: "Vf x10^3 (cm/s)", 1: "Vf x10^3 (mm/s)"}   # as printed in the column headers of that half of the table
CIT = "Link et al., Scientific Reports 2018 (DOI 10.1038/s41598-017-18398-4), Supplementary Table S1"
rows, count = [], {}
for half, s, d, o2, vg, dt, vf in A:
    count[s] = count.get(s, 0) + 1
    rows.append({
        "id": f"paper-link2018:{s}-{count[s]}", "source": "paper-link2018", "source_type": "paper", "material": "PMMA",
        "shape": f"{COLOR(s)} rod, {d} cm diameter" if COLOR(s) != "color not stated in Table S1" else f"rod, {d} cm diameter, color not stated in Table S1",
        "o2_start": o2, "o2_end": None, "flow_start": vg, "flow_end": None, "direction": "opposed",
        "outcome": "burning", "outcome_note": "", "gravity": "micro", "pressure_kPa": None,
        "spread_rate": vf, "sample_id": s,
        "flow_note": f"Flow step {count[s]} of this sample, lasted {dt} s. spread_rate is the number printed in Table S1 (column header: {HDR[half]}); the unit is unresolved because the two halves of the table print different units and the article text does not state one.",
        "flags": ["hand_entered"],
        "citation": f"{CIT}, sample {s}, flow step {count[s]}",
        "raw_spread_rate_header": HDR[half], "raw_step_seconds": dt, "raw_group": "paper-link2018",
    })
json.dump(rows, open(f"{D}/tests_link2018.json", "w"), indent=1)
print("rows written:", len(rows), "| first:", rows[0]["id"], rows[0]["o2_start"], rows[0]["flow_start"], rows[0]["spread_rate"])
