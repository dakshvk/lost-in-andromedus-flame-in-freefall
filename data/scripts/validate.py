# Fails loudly (exit 1) if tests.json breaks any rule.
import os
DATA_DIR = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))  # scripts live in data/scripts/
import json, sys, collections
D = DATA_DIR
t = json.load(open(f"{D}/tests.json")); bad = []
OUT = {"quenched","blow_off","no_ignition","burning","ignited_only","unknown"}
SRC = {"psi-25","psi-98","psi-99","psi-100","psi-20","paper-link2018","paper-saffire45"}
MAT = {"SIBAL","PMMA","Nomex","wax","silicone","other"}
FLG = {"o2_end_suspect","low_flow_uncertain","o2_reading_questioned","outcome_from_report_notes","outcome_from_zhao","hand_entered","context_only"}
def need(c, msg):
    if not c: bad.append(msg)
need(len({x["id"] for x in t}) == len(t), "duplicate ids")
for x in t:
    i = x["id"]
    need(x.get("citation"), f"{i}: no citation")
    need(x["outcome"] in OUT, f"{i}: bad outcome {x['outcome']}")
    need(x["source"] in SRC, f"{i}: bad source")
    need(x["material"] in MAT, f"{i}: bad material")
    need(set(x["flags"]) <= FLG, f"{i}: bad flag")
    need(x["o2_start"] is not None or "context_only" in x["flags"], f"{i}: o2_start null without context_only")
    if x["source_type"] == "paper": need("hand_entered" in x["flags"], f"{i}: paper row not hand_entered")
    if x["outcome"] != "unknown" and x["source"] == "psi-25": need(x["outcome_note"] or "outcome_from_report_notes" in x["flags"] or "outcome_from_zhao" in x["flags"], f"{i}: PSI-25 row has a known outcome but no note or outcome flag")
c = collections.Counter(x["source"] for x in t)
need(c["psi-25"] == 129, f"psi-25 rows {c['psi-25']} != 129")
need(c["paper-link2018"] == 52, "link2018 != 52")
need(c["paper-saffire45"] == 5, "saffire45 != 5")
need(c["psi-98"] == 2 and c["psi-99"] == 10 and c["psi-100"] == 2, "saffire I-III counts")
sib = collections.Counter(x["outcome"] for x in t if x["source"] == "psi-25" and x["material"] == "SIBAL")
need(dict(sib) == {"unknown":7,"quenched":6,"no_ignition":6,"burning":3,"blow_off":1,"ignited_only":4}, f"SIBAL outcomes {dict(sib)}")
if bad:
    print("FAIL"); [print(" -", b) for b in bad]; sys.exit(1)
print("OK:", len(t), "rows,", dict(c))
