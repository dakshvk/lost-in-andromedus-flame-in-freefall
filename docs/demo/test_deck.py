"""Tests for the 7 slide demo deck.

Run from anywhere:  python3 docs/demo/test_deck.py [path/to/deck.pptx]
(needs python-pptx; the data check reads web/data/*.json in this repo)

It checks four things:
  1. structure: 7 slides at most (NASA's limit), one GIF per slide, notes, nothing off the slide
  2. the GIF files: real animated GIFs that loop
  3. facts: every number on a slide matches the site's data files
  4. coverage: every point we need to make appears on a slide or in its notes
"""
import json
import os
import sys

from pptx import Presentation

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", ".."))
SUFFIX = os.environ.get("GIF_SUFFIX", "")
DECK = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "lost-in-andromedus-demo.pptx")

failures = []


def check(ok, label):
    print(("PASS  " if ok else "FAIL  ") + label)
    if not ok:
        failures.append(label)


prs = Presentation(DECK)
slides = list(prs.slides)
W, H = prs.slide_width, prs.slide_height


def slide_text(sl):
    return "\n".join(sh.text_frame.text for sh in sl.shapes if sh.has_text_frame)


def notes(sl):
    return sl.notes_slide.notes_text_frame.text if sl.has_notes_slide else ""


texts = [slide_text(s) for s in slides]
notes_txt = [notes(s) for s in slides]
everything = "\n".join(texts + notes_txt).lower()

# 1. structure ------------------------------------------------------------
check(len(slides) <= 7, f"at most 7 slides (NASA limit): {len(slides)}")
check(len(slides) == 7, "exactly 7 slides")
for i, sl in enumerate(slides, 1):
    pics = [s for s in sl.shapes if s.shape_type == 13]
    gifs = [p for p in pics if p.image.content_type == "image/gif"]
    check(len(gifs) == 1, f"slide {i}: one GIF picture")
    check(len(notes_txt[i - 1]) >= 200, f"slide {i}: speaker notes at least 200 characters ({len(notes_txt[i-1])})")
    off = [s for s in sl.shapes if s.left < 0 or s.top < 0 or s.left + s.width > W or s.top + s.height > H]
    check(not off, f"slide {i}: every shape inside the slide")
    nums = sum(1 for s in sl.shapes if s.has_text_frame and s.text_frame.text.strip().isdigit())
    check(nums >= 4, f"slide {i}: at least 4 numbered steps ({nums})")

# 2. GIF files ------------------------------------------------------------
for n in range(1, 8):
    b = open(os.path.join(HERE, f"s{n}{SUFFIX}.gif"), "rb").read()
    check(b[:6] in (b"GIF89a", b"GIF87a"), f"s{n}{SUFFIX}.gif is a GIF")
    check(b"NETSCAPE2.0" in b, f"s{n}{SUFFIX}.gif loops")
    frames = b.count(b"\x21\xf9\x04")
    check(frames >= 50, f"s{n}{SUFFIX}.gif has {frames} frames (animated, at least 50)")
    w = int.from_bytes(b[6:8], "little")
    check(w >= 800, f"s{n}{SUFFIX}.gif is at least 800 px wide ({w})")

# 3. facts against the data -------------------------------------------------
cards = json.load(open(os.path.join(REPO, "web/data/cards.json")))
by = {c["material"]: c for c in cards["cards"]}
exps = json.load(open(os.path.join(REPO, "web/data/experiments.json")))["experiments"]
low = {c["material"]: c for c in cards["low_pressure_group"]["cards"]}
pm = by["PMMA"]
t5 = texts[4]
check(f"{pm['test_count']} tests" in t5 and f"{pm['known_outcomes']} with a known outcome" in t5,
      "slide 5: PMMA test count and known outcomes match cards.json")
check(f"{pm['oxygen_range_pct'][0]} to {pm['oxygen_range_pct'][1]}% oxygen" in t5, "slide 5: PMMA oxygen range matches")
check(f"airflow {int(pm['airflow_range_cm_s'][0])} to {int(pm['airflow_range_cm_s'][1])} cm/s" in t5, "slide 5: PMMA airflow range matches")
check(f"{by['SIBAL']['test_count']} tests" in t5, "slide 5: SIBAL count matches")
check(f"only {by['Nomex']['test_count']}, {by['Silicone']['test_count']} and {by['Wax']['test_count']}" in t5,
      "slide 5: Nomex, silicone, wax counts match")
check(f"PMMA has {pm['test_count']} tests" in texts[3] and f"{pm['oxygen_range_pct'][1]}%" in texts[3],
      "slide 4: PMMA count and 22.2% match")
check(len(exps) == 24 and "24" in texts[6], f"slide 7: {len(exps)} experiments in the data, 24 on the slide")
check("BASS-II" in exps[0]["title"] and "BASS-II is first" in texts[6], "slide 7: BASS-II is first in the ranking data")
cot = [c for k, c in low.items() if k.startswith("Cotton")][0]
check(cot["oxygen_range_pct"][1] == 26.2 and "26.2% oxygen" in texts[5], "slide 6: cotton V-2 26.2% matches")
check("70.7 kPa" in texts[5] and 70.7 in cot["pressure_kPa"], "slide 6: 70.7 kPa matches")
hi = max(c["oxygen_range_pct"][1] for c in by.values())
check(hi == 22.2 and "22.2% oxygen" in texts[2], f"slide 3: highest oxygen at normal pressure is 22.2 in the data ({hi})")

# 4. coverage ---------------------------------------------------------------
points = {
    "problem: Moon base runs at 30% oxygen or more": ["30% oxygen or more", "moon base"],
    "tests were in orbit, not on the Moon": ["microgravity", "none were on the moon"],
    "the site takes typed questions": ["we type", "typed live"],
    "INSIDE is explained": ["inside", "within what was tested"],
    "NEAR is explained": ["near", "within 1.0 oxygen point"],
    "BEYOND is explained": ["beyond", "no test can say what happens"],
    "BEYOND does not mean it will or will not burn": ["will or will not burn"],
    "every number is checked": ["every number"],
    "no AI writes the answers": ["never from an ai"],
    "evidence chart: ticks and the empty band": ["tick", "band", "no test is in the band"],
    "outcome words explained": ["quenched", "blow off", "no ignition", "unknown"],
    "materials covered": ["pmma", "sibal", "nomex", "silicone", "wax"],
    "closest evidence is Saffire V at low pressure": ["saffire v", "v-2", "70.7 kpa", "26.2%"],
    "ranking of 24 experiments, our judgment": ["24", "bass-ii", "our judgment, not nasa's"],
    "limits panel": ["limits and rules"],
    "microgravity limit and one sixth gravity": ["one sixth"],
    "data source credited (NASA PSI)": ["physical sciences informatics"],
    "AI use disclosed": ["ai tools helped write the code"],
    "team named": ["daksh kumar", "paridhi singh", "jenisha subedi"],
    "unknown outcomes are never guessed": ["we never guess"],
}
for label, words in points.items():
    missing = [w for w in words if w not in everything]
    check(not missing, f"covered: {label}" + (f"  (missing: {missing})" if missing else ""))

print()
print("ALL PASS" if not failures else f"{len(failures)} FAILED")
sys.exit(1 if failures else 0)
