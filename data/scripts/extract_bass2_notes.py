# Written with SI assistance (Claude), reviewed by <teammate name - fill in>.
# Lane A Step 3 (part 1): pull "Test observations and anomalies" per test id from BASS-II report Appendix A.
import os
DATA_DIR = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))  # scripts live in data/scripts/
import pdfplumber, re, json, csv
PDF = "/tmp/bass/r.pdf"
ID = re.compile(r"^[A-Z]\d{1,2}[ab]?$")
out = {}      # test id -> dict
dups = []
with pdfplumber.open(PDF) as pdf:
    for pno in range(110, 121):          # pdf pages 111-121 (0-based 110-120)
        page = pdf.pages[pno]
        for tab in page.extract_tables():
            for row in tab:
                cells = [c for c in row]
                tid_idx = next((i for i, c in enumerate(cells[:10]) if c and ID.match(c.strip())), None)
                if tid_idx is None: continue
                tid = cells[tid_idx].strip()
                first = (cells[0] or "").replace("\n", " ")
                gmt = re.search(r"GMT\s*(?:2014\s*)?(\d+)\s*$", first)
                note = (cells[-1] or "").replace("\n", " ").strip()
                rec = {"id": tid, "pdf_page": pno + 1, "date_gmt_cell": first,
                       "gmt": gmt.group(1) if gmt else None, "note": note}
                if tid in out: dups.append(tid)
                out[tid] = rec
print("ids found in Appendix A:", len(out), "| duplicates:", dups)
json.dump(out, open(os.path.join(DATA_DIR, "bass2_appendixA_notes.json"), "w"), indent=1)

# compare with PSI-25
rows = list(csv.reader(open(os.path.join(DATA_DIR, "raw/PSI-25_Experimental table_BASS-II.csv"), encoding="utf-8-sig", newline="")))[1:]
psi = {r[1]: r for r in rows if r and r[1]}
missing = [t for t in psi if t not in out]
extra = [t for t in out if t not in psi]
print("PSI-25 ids:", len(psi), "| matched:", len(psi) - len(missing), "| NOT in Appendix A:", missing)
print("in Appendix A but not in PSI-25:", extra)
blank = [t for t in psi if t in out and not out[t]["note"]]
print("matched but blank note:", blank)
gm = [(t, psi[t][3], out[t]["gmt"]) for t in psi if t in out and out[t]["gmt"] and out[t]["gmt"].lstrip("0") != psi[t][3]]
print("GMT mismatches (id, psi, report):", gm)
