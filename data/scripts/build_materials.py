# Computes materials.json from tests.json. Nothing here is typed by hand: every number is counted from the rows.
# Link 2018 rows are all "burning with a spread rate" and have no ignition outcomes, so they are counted separately.
import os
DATA_DIR = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))  # scripts live in data/scripts/
import json, collections
D = DATA_DIR
t = json.load(open(f"{D}/tests.json"))
mats = {}
for m in sorted({x["material"] for x in t}):
    rows = [x for x in t if x["material"] == m]
    core = [x for x in rows if x["source"] != "paper-link2018"]
    oc = collections.Counter(x["outcome"] for x in core)
    o2 = [x["o2_start"] for x in core if x["o2_start"] is not None]
    fl = [x["flow_start"] for x in core if x["flow_start"] is not None]
    mats[m] = {
        "rows_total": len(rows),
        "rows_excluding_link2018": len(core),
        "outcomes": dict(sorted(oc.items())),
        "spread_rate_rows_link2018": sum(1 for x in rows if x["source"] == "paper-link2018"),
        "sources": dict(sorted(collections.Counter(x["source"] for x in rows).items())),
        "o2_start_range": [min(o2), max(o2)] if o2 else None,
        "flow_start_range_cm_s": [min(fl), max(fl)] if fl else None,
        "computed_from": "tests.json by build_materials.py",
    }
json.dump(mats, open(f"{D}/materials.json", "w"), indent=1)
for m, v in mats.items(): print(m, v["rows_total"], v["outcomes"])
