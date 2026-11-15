import os
DATA_DIR = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))  # scripts live in data/scripts/
import json
from pages_data import PAGES
D=os.path.join(DATA_DIR, "experiments.json"); d=json.load(open(D))
for o in d:
    p=PAGES.get(o["psi_id"])
    if not p: continue
    for k,v in p.items(): o[k]=v
    o["sub_research_area_note"]="read from the PSI page text pasted by the Lane A owner"
    o["summary_basis"]="written by us from the Objectives text on the PSI page (pasted page text)"
OURS={"PSI-26":(122,"our PSI-26 CSV: 122 table lines, of which 1 is a 'SOOT Cleaning' line and 121 are tests (PSI page shows 123)"),
      "PSI-21":(32,"our PSI-21 CSV: 32 test-day summary rows (PSI page shows 33); rows are days, not single burns"),
      "PSI-47":(2,"our PSI-47 CSV: 2 dust-measurement sessions (D1, D2 on 2005 GMT 54 and 63); not burns"),
      "PSI-20":(18,"our PSI-20 CSV: 18 day-summary rows (PSI page shows 19); rows are days, not single burns")}
for o in d:
    if o["psi_id"] in OURS: o["test_count"],o["test_count_source"]=OURS[o["psi_id"]]
json.dump(d,open(D,"w"),indent=1)
print("pages applied:",sorted(PAGES), "| sub-area known:",sum(1 for o in d if o["sub_research_area"]),"of",len(d))
