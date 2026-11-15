# Written with SI assistance (Claude), reviewed by <teammate name - fill in>.
# Saffire IV/V rows from ICES-2021-266 (NTRS 20210011521), Table 1 + outcome text.
# Double entry, as the plan requires, done two independent ways (no second person available yet):
#   A) script reads Table 1 from the PDF text layer
#   B) values typed by hand from the page-3 image (rendered at 120 dpi and read by eye)
# Then both are compared and every quoted outcome phrase is checked to exist in the paper.
import os
DATA_DIR = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))  # scripts live in data/scripts/
import json, re, subprocess

PDF = "/tmp/saf/s.pdf"
D = DATA_DIR
page3 = subprocess.run(["pdftotext", "-layout", "-f", "3", "-l", "3", PDF, "-"], capture_output=True, text=True).stdout
fulltext = subprocess.run(["pdftotext", PDF, "-"], capture_output=True, text=True).stdout
norm = lambda s: re.sub(r"\s+", " ", s.replace("’", "'")).strip()
FT = norm(fulltext)

# ---------- entry A: from the PDF text layer ----------
def row_numbers(label, n=5):
    for line in page3.splitlines():
        if line.strip().startswith(label):
            nums = re.findall(r"\d+(?:\.\d+)?", line[len(line) - len(line.lstrip()) + len(label):])
            if len(nums) >= n: return [float(x) for x in nums[:n]]
    raise SystemExit(f"entry A: row not found: {label}")
def row_words(label):
    for line in page3.splitlines():
        if line.strip().startswith(label): return re.findall(r"Concurrent|Opposed", line)
    raise SystemExit("entry A: direction row not found")
tests = ["IV-1", "IV-2", "V-2", "V-3", "V-4"]
A = {"length": row_numbers("Length (cm)"), "flow": row_numbers("Air Flow Rate (cm/s)"),
     "kpa": row_numbers("Ambient Pressure (kPa)"), "dir": row_words("Flow Direction")}
# oxygen label wraps over two lines in the text layer
o2line = next(l for l in page3.splitlines() if "Oxygen Concentration" in l)
A["o2"] = [float(x) for x in re.findall(r"\d+\.\d", o2line)][-5:]

# ---------- entry B: typed by hand from the page image ----------
B = {"length": [50, 18, 50, 18, 20], "flow": [20, 20, 20, 20, 20],
     "kpa": [100.0, 100.0, 70.7, 71.3, 72.6], "o2": [22.0, 22.0, 26.2, 25.4, 25.7],
     "dir": ["Concurrent", "Concurrent", "Concurrent", "Concurrent", "Opposed"]}
diffs = [(k, A[k], B[k]) for k in B if [str(x) for x in A[k]] != [str(x) for x in B[k]] and A[k] != B[k]]
print("Entry A vs entry B differences:", diffs if diffs else "none (both entries agree on all 25 values)")
assert not diffs

# ---------- outcome phrases: verbatim, each must appear in the paper ----------
Q = {
 "IV-1": "established a steady opposed spread rate and flame size",
 "IV-2": "keep the flame alive over the 15 second interval of no flow",
 "V-2": "the flame grew back when the flow was turned on again",
 "V-3": "the flame extinguished quickly when the flow was turned off",
 "V-4": "the rapid extinction after 300 seconds of cooling at low air flow",
}
for t, q in Q.items():
    assert norm(q) in FT, f"quote for {t} not found in paper text"
    assert len(q.split()) < 15
print("All 5 outcome phrases found verbatim in the paper (each under 15 words).")

CIT = "Saffire IV and V paper, ICES-2021-266 (NASA NTRS 20210011521, ntrs.nasa.gov/citations/20210011521)"
spec = {
 "IV-1": dict(material="SIBAL", shape="fabric, 50 cm long, 40 cm wide (Table 2 lists 41 cm)", outcome="burning", flow_end=20,
              flow_note="Table 1 gives 20 cm/s; no flow change is stated for this test. Section C text calls the spread 'opposed' but Table 1 says Concurrent; Table 1 used.",
              cite=f"{CIT}, Table 1 and Section C"),
 "IV-2": dict(material="PMMA", shape="2 sided slab, 1 cm thick, 18 cm long", outcome="burning", flow_end=5,
              flow_note="Table 1 gives 20 cm/s. Paper text: flow was cut to 5 cm/s for 65 s, then turned off abruptly; flame stayed alive through 15 s of no flow.",
              cite=f"{CIT}, Table 1 and Figure 4"),
 "V-2": dict(material="other", shape="cotton jersey fabric, 50 cm long, 40 cm wide (Table 2 lists 41 cm)", outcome="burning", flow_end=None,
             flow_note="Table 1 gives 20 cm/s. Fan was turned off at about 280 s for 70 s, then flow was turned on again (Figure 3); the speed after restart is not stated, so flow_end is empty.",
             cite=f"{CIT}, Table 1 and Figure 3"),
 "V-3": dict(material="PMMA", shape="1 sided slab, 0.5 cm thick, 18 cm long", outcome="quenched", flow_end=5,
             flow_note="Table 1 gives 20 cm/s; flow was reduced to 5 cm/s and held for 300 s, then the fan was turned off (Figure 5). The flame went out after a planned fan stop, not at a flow limit.",
             cite=f"{CIT}, Table 1 and Figure 5"),
 "V-4": dict(material="PMMA", shape="structured slab (grooves and ridges), 1 cm thick, 20 cm long", outcome="quenched", flow_end=5,
             flow_note="Table 1 gives 20 cm/s; flow was reduced to 5 cm/s and held for 300 s, then the fan was turned off (Figure 6). The flame went out after a planned fan stop, not at a flow limit.",
             cite=f"{CIT}, Table 1 and Figure 6"),
}
rows = []
for i, t in enumerate(tests):
    s = spec[t]
    rows.append({
        "id": f"paper-saffire45:{t}", "source": "paper-saffire45", "source_type": "paper", "material": s["material"],
        "shape": s["shape"], "o2_start": B["o2"][i], "o2_end": None, "flow_start": B["flow"][i], "flow_end": s["flow_end"],
        "direction": B["dir"][i].lower(), "outcome": s["outcome"], "outcome_note": Q[t], "gravity": "micro",
        "pressure_kPa": B["kpa"][i], "spread_rate": None, "sample_id": t, "flow_note": s["flow_note"],
        "flags": ["hand_entered"], "citation": s["cite"],
        "raw_material": {"IV-1": "SIBAL Cloth", "IV-2": "2-sided PMMA", "V-2": "Cotton Jersey", "V-3": "1 sided PMMA", "V-4": "Structured PMMA"}[t],
        "raw_group": "paper-saffire45",
    })
json.dump(rows, open(f"{D}/tests_saffire45.json", "w"), indent=1)
print("rows written:", len(rows))
for r in rows: print(r["id"], r["material"], r["o2_start"], r["pressure_kPa"], r["flow_start"], r["flow_end"], r["direction"], r["outcome"])
