# Chronicle

A running record of what was added to this repository, by whom, why, and how. Add an entry every time you add or change something, in the same commit as the change.

Newest entries go at the top, right under the line that says "Entries start here".

## How to write an entry

Copy this block, fill it in, and paste it at the top of the entries.

```
### <date and time> | <your name> | <short title>
- What: the files or parts you added or changed
- Why: the reason, in one or two sentences (what problem it solves or which lane it belongs to)
- How: what you did, step by step, including any tool or AI used, so someone else could repeat it
- Check: how you or someone else confirmed it works or matches the source
```

Rules:

- Say what actually happened, including anything that did not work.
- If SI (AI) helped, say which tool and for what. Also add a line to `AI_USE_LOG.md`.
- Never edit or delete an old entry. If it was wrong, add a new entry that corrects it.

---

Entries start here

### 2026-11-15 00:30 | Daksh | Lane C: readable evidence chart, design guidelines, phone fixes

- What: new `web/js/coverage.js` is the main evidence view (one row per material on a shared oxygen axis, one tick per test, ending at the empty 30% Moon band). The oxygen x airflow scatter moved behind a "Show every test" button and was decluttered (tests at their starting airflow, no flow-change lines, no separate no-flow strip, no pressure text). Standard material rows and graphs no longer include the low-pressure Saffire V tests (PMMA 102, matching the card). Tooltips say where each outcome was read from; the Moon caption says the view is illustrative. Design tokens follow the team's website guidelines: charcoal and graphite panels, amber for combustion, 4 to 8 px radii, monospace for measurements, smaller headline. Phone width: no sideways scroll.
- Why: Daksh found the scatter "extremely messy and hard to read", asked for minimal AI slop and a page that can be demoed in 30 seconds, and shared the team's design guidelines.
- How: with Claude Code, no Fable.
- Check: in the browser at desktop and 375 px phone width: no console errors, no horizontal scroll, coverage rows match the cards (102, 32, 4, 4, 1, 3 = 146 tests), and the demo path works (PMMA at 30% BEYOND and opens the PMMA card; cotton at 26% shows Saffire V-2 at 70.7 kPa; smoke detection finds SAME; BASS-II tops the ranking with its reasons).

### 2026-11-14 22:50 | Daksh | Lane C website built (branch lane-c-ui, CP1 to CP5) and an anti-slop pass

- What: `web/index.html`, `web/css/styles.css`, `web/js/` (app, moon, chart, materials, answer, ranking, limits, dom) and `web/assets/` (NASA Moon color and elevation textures, two inspiration images). The page has the 3D Moon with material markers that spin with it, hover previews and click-through material detail, the ask box and answer panel, the evidence map, material cards, the investigation ranking and the limits drawer. Moon styles can be compared with `?moon=nasa` (default), `procedural`, `photo` and `illustration`.
- Why: Lane C, built to Part 5 of the team doc and Daksh's design (a realistic spinning Moon with the materials on it). Daksh then asked for minimal AI slop and a page that can be demoed in 30 seconds.
- How: a Fable agent (Claude Fable 5.2) wrote CP1 to CP4 and started CP5 before the usage limit hit; Claude Code checked and finished CP5. Daksh decided Fable is not to be used by default (it burns usage and makes slop). Anti-slop pass, checked against the public AI-slop catalogs: heading is solid white (no gradient text), the button is a solid color, the gradient bar on every card is gone, backdrop blur is down from 7 elements to 2 (header and floating button), decorative glows on dots and bars are gone, "Inter" is dropped from the font stack, and the ranking shows the top 5 with a "Show all 24" button. NASA texture: SVS CGI Moon Kit (lroc_color_2k.jpg, ldem_3_8bit.jpg), credited in the footer and limits drawer. The illustration variant carries a visible "SI-generated image" label.
- Check: server started with `python3 -m uvicorn api.app:app --port 8000`; no console errors; "Will PMMA burn at 30% oxygen?" returns BEYOND with evidence M2, M5, M14, the Saffire V nearest evidence and the corrected gravity note, and opens the PMMA card and graph (102 tests, 76 known); no horizontal scroll at phone width; no broken images; every button named; all four `?moon=` styles load with no errors; after the anti-slop pass the page still loads clean. Logic 93 passed, API 13 passed. Not checked: hover previews by mouse, touch on a real phone, a full size look at the lower sections.
- Open: the photo variant's source is unknown and needs a credit before it could be used in the submission; links to the exact page of each cited source are not built (the data has no page numbers); a sparkle star can overlap the caption text.

### 2026-11-14 23:40 | Daksh | Merged Lane B v11.1 (PR #4), oxygen and airflow questions checked together

- What: merged Paridhi's PR #4 (v11.1: the cotton, known-outcome and no-oxygen-count fixes mirrored into the airflow-only answer) into main on top of the PR #2 merge and the gravity note fix. Regenerated logic/ask_samples.json and web/data/ so the saved answers carry the new gravity note.
- Why: airflow-only questions still had the three v11 bugs ("Is 20 cm/s airflow inside our data for cotton?" said INSIDE with 0 tests). The earlier 168-question check only asked oxygen questions, so it missed them.
- How: merged with git (no conflicts), then reran everything with Claude Code.
- Check: validate.py OK; `python3 -m pytest -q logic` 93 passed; `python3 -m pytest -q api` 13 passed; 0 number-check failures in the saved answers; a 194-question sweep (oxygen with and without airflow, airflow-only per material, airflow-only with no material, cotton airflow) gave verdicts matching each material's card ranges, counts matching the cards (143 overall, SIBAL 32), known-outcome evidence and no unknown test ids.

### 2026-11-14 23:10 | Daksh | Merged Lane A update (PR #2), checked Lane A and Lane B together, gravity note fix

- What: merged PR #2 (Jenisha: Link spread rate in cm/s, 100 kPa for Saffire I S1 and Saffire II 2-5 and 2-6, validate.py fix, README count). Resolved the AI_USE_LOG.md conflict by keeping every row. `logic/answer.py`: the gravity note names the experiments with a pressure ("Saffire I, Saffire II and Saffire IV/V", 8 tests) instead of "the 8 PSI-98 and PSI-99 and Saffire IV/V tests", and says the tests were on the ISS or in Cygnus cargo ships (the Saffire burns were in Cygnus, not on the ISS). Updated the one test that quoted the old wording; regenerated logic/demo_answers.json, logic/ask_samples.json and web/data/.
- Why: Lane A's new pressures made one Lane B test fail and the note read badly; the old note also said every test was on the ISS.
- How: with Claude Code. Checked the Link unit against the Table S1 PDF: the header is "Vf x10^3 (cm/s)", so 5.23 means 0.00523 cm/s; the right half's "(mm/s)" header has numbers the same size as the left half and as Table S2 (cm/s), so it reads as a typo, as Jenisha said.
- Check: validate.py prints OK (it can fail now); `python3 -m pytest -q logic` 89 passed; `python3 -m pytest -q api` 13 passed; a sweep of 168 questions (every standard material at oxygen and airflow inside, at the edge, just outside and far outside its card range) gave verdicts matching the card ranges, 0 number-check failures and no unknown test ids; a live uvicorn run answered PMMA at 30%, cotton at 26% and a smoke-detection question correctly.
- Not merged: PR #3 ("Lane B v11.1: airflow mirrors") is set up backwards (base is Paridhi's branch, head is main) and her branch has no new commits, so her airflow fixes are not on GitHub yet.
- Open: PSI-100 S1 looks like ICES Table 2 sample III-1 (100 kPa) but has no pressure yet.

### 2026-11-14 20:55 | Daksh | Merged Lane B, tested everything together, Lane C data layer and API

- What: merged PR #1 (Lane B) into main. New: `web/export_data.py` (builds `web/data/*.json` for the site), `web/data/` (tests, cards, experiments, investigations, limits, demo_answers, meta), `web/js/data.js` (the page's data module, with offline fallback), `api/app.py` (FastAPI: `/api/health`, `/api/ask`, `/api/data/{name}`, serves `web/`), `api/test_api.py` (13 tests), `web/README.md`, `requirements.txt`. Changed: `logic/rag.py` loads `investigations.csv` from next to the file, so the API works from any folder.
- Why: Lane C, option A (Python API plus static site). Design comes later; this is only the data the page will read, built from Lane A's data through Lane B's code so the site and the answers can never disagree.
- How: written with Claude Code. Cards count and range only rows that are not Link et al. and have an oxygen value, the same rule the answers use. Hardware groups in investigations.json are copied from NASA's challenge notes (source in the file).
- Check: `data/scripts/validate.py` prints OK; `python3 -m pytest -q logic` gives 89 passed; `python3 -m pytest -q api` gives 13 passed; 21 questions through ask() all pass the number checker; a real `uvicorn api.app:app` run answered "Will PMMA burn at 30% oxygen?" with BEYOND and served the cards and `js/data.js`. Card numbers match the answers (PMMA 102 tests, 76 known; SIBAL 32, 23 known).
- Open: "Will it burn?" (no material, no oxygen) goes to retrieval and returns ACME instead of asking for a material and oxygen. The cards.py text fields contradict themselves (PMMA "154 tests" next to "76 of 102"), so the export uses structured numbers only.

## 2026-11-14 20:48 PT — Paridhi Singh — Lane B v11.1: airflow mirrors of the v11 fixes

- **What:** build_airflow_answer now mirrors the three v11 fixes: a material with no standard-pressure rows (Cotton) returns BEYOND with its own low-pressure Saffire V rows as evidence and nearest evidence instead of the hardware band with 0 tests; the count skips rows with no oxygen value (143, not 145; SIBAL 32, not 34); the evidence sort prefers rows with a known outcome (doc Step 1.2). Evidence rows now carry pressure_kPa. 4 new tests; demo_answers.json + ask_samples.json regenerated (20 samples).
- **Why:** v11 fixed these three things on the oxygen side only. The airflow side still said "Cotton at 20 cm/s" is INSIDE with "0 tests" and an empty evidence list, counted 145/34 while the oxygen side said 143/32, and showed unknown-outcome rows (O1, T1, T5) as evidence.
- **How:** answer.py (low_rows saved before the standard-pressure filter, no-rows guard with the low-pressure nearest evidence, count excludes no-oxygen rows, evidence_pool prefers known outcomes); test_answer.py (TestV11_1Airflow, 4 tests); generate_samples.py (3 new airflow questions, notes to v11.1); samples regenerated.
- **Check:** 93 tests pass (89 + 4 new); 0 number checks failing; "Cotton at 20 cm/s airflow?" returns BEYOND with V-2 (70.7 kPa, burning); "What about 20 cm/s airflow?" says 143 tests; SIBAL airflow says 32 tests; airflow evidence rows all have outcomes.

### 2026-11-14 20:30 | Daksh | Lane B v11: cotton, known-outcome evidence, counts without blank oxygen

- What: `logic/cards.py` names the Saffire V-2 cotton jersey "Cotton" (Lane A records it as "other"); `logic/rag.py` adds "cotton" to the material matcher; `logic/answer.py`: closest_rows prefers rows with a known outcome, a material that exists only at low pressure (Cotton) shows its own Saffire V rows as evidence and nearest evidence instead of other materials' rows, the INSIDE/BEYOND count skips rows with no oxygen value, and evidence rows carry pressure_kPa; tests updated and 3 new tests added; demo answers and ask samples regenerated.
- Why: in v10, "Will cotton burn at 26% oxygen?" showed PMMA tests B1, B2, B3 as evidence even though Saffire V-2 is cotton at 26.2% oxygen and 70.7 kPa; evidence rows for PMMA at 30% were B1, B2, B3 (unknown outcomes) while M2, M5, M14 at the same 22.2% are quenched (doc Step 1.2: use rows with a known outcome); the no-material count (145) included the 2 Saffire III rows that have no oxygen value.
- How: edited the three files with Claude Code, updated the tests that encoded the old behaviour (Moon-base evidence is now F1, M2, M5; no-material count 143; V-2 labeled Cotton), added TestV11Answers, then ran `python3 generate_samples.py` in `logic/`.
- Check: `python3 -m pytest -q` in `logic/` gives 89 passed; demo_answers.json and ask_samples.json have 0 failing number checks; cotton at 26% returns BEYOND with V-2 (70.7 kPa, burning) as evidence; SIBAL at 18% evidence rows all have an outcome; count is 143 with no material and 32 for SIBAL.

## 2026-11-14 20:04 PT — Paridhi Singh — Lane B v10: material names, no-material count, gravity note

- **What:** Material names canonicalised (tests.json "wax"/"silicone" → "Wax"/"Silicone") and the matcher extended (silicone, candle → Wax), so "Silicone at 22%" and "a candle at 17%" are recognised; ask() passes the full rows to build_answer so classify's too-few-rows rule fires (wax: BEYOND, "Only 1 Wax test"); no-material count drops Link rows (145, not 200); INSIDE sentence names the airflow too when one was given; gravity note says pressure was recorded only for the 5 Saffire IV/V tests (70.7–100.0 kPa) and the BASS-II tables give none; closest_rows matches with \_same_material (PMMA ≡ "PMMA / other" on the CSV path).
- **Why:** PR #1 review (Daksh, Nov 14 — v9 is "the strongest round yet", merges cleanly, all 76 tests pass). The wax bug had two causes: the case mismatch (matcher "Wax" vs rows "wax") and ask() passing the 1-row pool, so the too-few-rows rule never saw a real dataset.
- **How:** cards.py (\_canonical_material), rag.py (MATERIAL_NAMES + silicone/candle), answer.py (ask full rows, count, INSIDE sentence, gravity_note, build_airflow_answer count), classifier.py ("coverage" key on the too-few/no-rows BEYOND); 10 new tests; demo_answers.json + ask_samples.json regenerated (17 samples).
- **Check:** 86 tests pass in the sandbox with the fixed main data; number checks failing: 0; answer.py **main** runs clean; ranking.py leaves data/experiments.json untouched. Margin definition CONFIRMED by Daksh: 25% of the range width, both sides, low clamped at 0.

## 2026-11-14 19:40 PT — Paridhi Singh — Lane B v9: per-material flow range, material counts, Lane A flag

- **What:** Per-material flow range with the 25% margin in classify() (PMMA 45 cm/s → BEYOND); ask() forwards the airflow in % questions; closest rows rank by oxygen + flow; INSIDE sentence quotes the material's count without Link rows (PMMA 102, not 200); lowest-airflow note when all tie rows carry the low-flow flag; gravity note shows the pressure range from the data (70.7–100.0 kPa); cards use Lane A's low_flow_uncertain flag and exclude Link rows from outcome counts (PMMA 76 of 102); number checker no longer crashes on blank oxygen; ranking.py no longer writes scores into data/experiments.json (web lane reads logic/ranked_experiments.json).
- **Why:** PR #1 review (Daksh, Nov 14): the classifier checked every material against the hardware limit (55 cm/s), and ask() dropped the airflow, so "PMMA at 20% and 45 cm/s" came back INSIDE. Daksh corrected his v7 note: the 49 cm/s rows were not the cause.
- **How:** classifier.py (FLOW_MARGIN = 0.25, material_flow_range()), answer.py (ask/closest_rows/build_answer/build_airflow_answer/gravity_note), cards.py, number_checker.py, ranking.py; 22 new/updated tests; demo_answers.json + ask_samples.json regenerated (13 samples).
- **Check:** 76 tests pass in the sandbox with Jenisha's fixed main data (including the 2-restrictor test, now green); number checks failing: 0; answer.py **main** runs clean.

## 2026-11-14 18:50 PT — Paridhi Singh — answer.py demo uses the full dataset; Saffire V rows stay out of the evidence pool

- What: two fixes found in the v8 Mac run. (1) answer.py's **main** demo questions used the 6-row sample while the stats came from tests.json, so "14% oxygen for SIBAL?" quoted the sample's SIBAL range (18.5–20.8%) next to the full 200-test stats. The demo now loads the full rows (tests.json, else the PSI CSV, else the sample) and uses them for every question. (2) build_answer and build_airflow_answer now use only standard-pressure rows for the verdict, ranges, and evidence: the low-pressure Saffire V rows (~71 kPa) had stretched the overall oxygen range to 26.2%, so 24% oxygen read INSIDE and the 30% Moon-base answer cited the Saffire V rows as its evidence. Now 24% is BEYOND, the 30% evidence is B1/B2/B3 (22.2%), and Saffire V is cited only in nearest_evidence. Three new tests lock this in (24% BEYOND, 25.4% BEYOND, 30% evidence is B1/B2/B3 with Saffire V in nearest_evidence). demo_answers.json regenerated (Q1 evidence is now B1/B2/B3); 53 of 54 tests pass, the 1 failure is the 2-restrictor data test by design.
- Why: the v8 Mac run showed both mismatches in the printed demo answers; the saved demo_answers.json (from generate_samples.py) had the same evidence problem for Q1.
- How: Written with SI assistance (Muse), reviewed by Paridhi Singh. Verified in the VM: with tests.json the SIBAL answer quotes 16.4–22.1% (evidence T9, T10, T12); 24% is BEYOND; 30% evidence is B1/B2/B3 with Saffire V in nearest_evidence; with tests.json hidden the demo falls back to the sample and quotes 18.5–20.8% with the fallback note.
- Check: python3 answer.py; python3 -m unittest test_classifier test_number_checker test_answer test_ranking test_swap -v.

## 2026-11-14 17:45 PT — Paridhi Singh — Ranking + swap Lane B to tests.json (v7)

- What: Scored all 24 experiments in data/experiments.json with the Step 2 rules (solid +3, spacecraft fire safety +3, table +2, flight +2, microgravity +1, 20+ tests +1); ties by test count then title. Top: BASS-II 12, BASS 12, SAFFIRE-III 11. Lane B now reads data/tests.json (200 rows) via cards.rows_from_tests_json(): stats 200 tests, O2 13.6–22.2% at standard pressure, 32 rows above 21%. Saffire V rows stay labeled by pressure ("PMMA (Saffire V, 71.3 kPa)") and are excluded from extremes, so the highest oxygen tested stays 22.2% (14 tests). SIBAL range is now 16.4–22.1% (Saffire II joins at standard pressure). SIBAL lowest airflow is now 1.0 cm/s in 3 tests (T4, T5, T13) — T6 has no end flow recorded in tests.json for its "5 2 1 <1" Air display. Correction to the v5 entry above: highest airflow is 53.0 cm/s (T17), not 49.0 — O5b/O13a's 49 was a fan reading, not a flow (parser fix, v6). 45 unit tests pass; demo answers + ask samples regenerated, 0 number checks failing.
- Why: Daksh's status check on main — ranking (Step 2) was the top remaining item, plus the swap to Lane A's tests.json once it landed, and the v5 review's airflow parser fix.
- How: Written with SI assistance (Muse), reviewed by Paridhi Singh. Ranking computed from data/experiments.json; swap verified against the cloned repo (validate.py OK, 200 rows). Tested in the VM (keyword fallback for RAG): all 45 tests pass; embedding ranking to be confirmed on the Mac with the real model.
- Check: python3 -m unittest test_classifier test_number_checker test_answer test_ranking test_swap -v; python3 ranking.py; python3 generate_samples.py; python3 answer.py; python3 rag.py.

## 2026-11-14 16:55 PT — Paridhi Singh — Address third RAG review (v5)

- What: Router reordered (unit numbers and highest/lowest checked first, name check for investigations only); whole-word case-aware name matching (lowercase "same" and "flexible" no longer match SAME/FLEX); exact lookup returns every investigation named (BASS + BASS-II, all three Saffire, both ACME); added min_oxygen() (13.6%, O12), min_airflow() (0.0 cm/s, O2) and max_airflow() (49.0 cm/s, O5b and O13a) over the full 129 rows with all ties, number-checked; added ask(question) as the website's single call; demo_answers.json now has 6 answers (Q5 lowest oxygen, Q6 highest airflow).
- Why: Daksh's third RAG review on PR #1 — one blocker (material names sent number questions to RAG) plus smaller items, and the AI log table fix.
- How: Written with SI assistance (Muse), reviewed by Paridhi Singh. Min/max values computed from the full PSI-25 CSV. Tested in the VM (keyword fallback): all three blocker questions route to code with correct answers; BASS/BASS-II, Saffire I/II/III and pizza cases all pass; embedding ranking to be confirmed on the Mac with the real model.
- Check: python3 rag.py, python3 answer.py run clean.

### 2026-11-14 16:50 | Daksh | Status check: what Lane B still needs, what Lane A will fix, what is left to build

- What: this entry only. No code changed. It records where the project stands at Paridhi's PR #1 commit `337fe96` (feat/lane-b-agent, 16:36), compared against the Lane B steps in the team doc ("Flame in Freefall: Findings, Team Plan and Lane Instructions", Part 4).
- Why: so all three of us can see what is done, what is blocked on Lane A, and what nobody has started, with about 31 hours left (deadline Sun Nov 15, 11:59 PM).
- How: Claude Code read the PR branch, ran the logic code with the real embedding model, recounted numbers from `data/raw/PSI-25_Experimental table_BASS-II.csv`, and compared the result with the team doc. Daksh reviewed it.
- Check: every number below was recounted from the CSV or read from the cited source on Nov 14.

**Lane B: built (on PR #1, not merged yet)**

- Classifier: INSIDE / NEAR / BEYOND / NEED_OXYGEN, per material oxygen ranges, NEAR = 1.0 oxygen point.
- Number checker and answer builder, with a gravity note on every answer.
- Material cards built from the full CSV: PMMA/other 98 tests, SIBAL 27, Nomex 3, Wax 1.
- Highest oxygen answer: 22.2%, all 14 tied tests (B1, B2, B3, B4, B5, B7, B12, F1, M1, M2, M5, M14, O1, O2), number checked.
- RAG v4: router, a corpus of 10 investigations (`logic/investigations.csv`) plus the cards, cached embeddings (all-MiniLM-L6-v2), score cutoff 0.30, exact PSI ID lookup.
- Saffire V nearest evidence note for 30%+ oxygen, cited to Urban et al., ICES 2021, Table 1 (NTRS 20210011521): 25.4 to 26.2% O2 at 70.7 to 72.6 kPa, 20 cm/s.
- Three saved demo answers (`logic/demo_answers.json`).

**Lane B: open from the v4 review (review 5908233652)**

- Blocker: material names (PMMA, SIBAL, Nomex) are checked before numbers, so "Is 30% oxygen inside our data for PMMA?" goes to RAG instead of code.
- Names match inside other words ("the same hardware" returns SAME, "flexible" returns FLEX).
- A comparison like "BASS vs BASS-II" returns only one investigation.
- Only max oxygen has code; min oxygen and min/max airflow do not.
- AI use log table has an empty row and lines outside the table.

**Lane B: not started (from the team doc)**

- Step 2, ranking: `experiments.json`, a score per investigation with a "why it ranked here" breakdown. The challenge asks the dashboard to rank investigations, so this is the most important missing piece.
- Unit tests: none in the repo. The doc lists required cases for the classifier (Step 1.9) and the number checker (Step 4.4).
- Step 5, the hand off to the website: one `ask(question)` function, the endpoints or shared code the site calls, and a sample response for each.

**Lane B: partly done**

- Airflow range is the hardware maximum (55 cm/s, NEAR up to 65) for every material. The doc says each material's own tested flow range with a 25% margin.
- No "fewer than 3 rows means extrapolated" rule (Wax has 1 row).
- Nearest rows rank by oxygen only. The doc says oxygen and flow, each scaled by the material's range.
- No spread rate questions (these use the Link et al. rows).
- The gravity note does not show the pressure range from the data.

**Lane A: what it still needs to deliver**

- Nothing from Lane A is in the repo yet besides the raw PSI-25 copy, and there is no `contract.md` with the frozen column list.
- The shared tests table in the contract shape: outcome, flow_start / flow_end, pressure_kPa, source on every row.
- SIBAL outcomes from the Zhao et al. 2015 appendix (27 rows, joined on GMT day of year plus Test #).
- PMMA outcomes from the BASS-II report Appendix A notes (NASA/TM-20210011385), since PSI-25 has no outcome column.
- Saffire IV/V rows from ICES 2021 Table 1, and the 52 Link et al. 2018 Table S1 rows with spread_rate.
- The other seven PSI tables (PSI-20, 21, 26, 47, 98, 99, 100) saved in `data/raw` with SHA-256, like PSI-25. PSI answered requests again on the afternoon of Nov 14.

**What Lane A fixes by itself once it lands**

- Rows get real outcomes, so the classifier can use only rows with a known outcome, as the doc says.
- Proper flow_start / flow_end per row, so per material flow ranges become possible.
- pressure_kPa, so the gravity note can show the real pressure range.
- Saffire and Link rows arrive in the same table, and Paridhi's own PSI-25 parser can be retired.

**What Lane B still has to change after Lane A lands**

- Read Lane A's table instead of the raw CSV, then rebuild the cards and demo answers.
- Per material flow ranges, the too-few-rows rule, scaled nearest rows, Link rows kept out of outcome answers, spread rate questions.

**Decisions the team needs to make**

- PMMA outcome coverage: if Lane A cannot fill most PMMA outcomes from Appendix A, a strict "known outcome only" rule turns many PMMA questions into extrapolated.
- Saffire IV/V rows ran at about 71 kPa, not normal pressure. If they join the PMMA range, "PMMA at 25%" becomes INSIDE. Keep them out of the ranges, or label them by pressure.
- Confirm NEAR = 1.0 oxygen point and write the chosen margins in the website's limits drawer.

**Still to build, any lane**

- The website: `web/` is empty.
- An investigation summary and compare view, covering what NASA's challenge notes list: objectives, fuels (shape and size), conditions, what varied, sensors, and shared hardware (BASS, BASS-II, SPICE and SLICE used the same MSG flow duct).
- The References list for the submission, including sentence-transformers and all-MiniLM-L6-v2, ICES 2021 (NTRS 20210011521), and NASA's FM2 LPSC 2026 presentation (NTRS 20260001966) if FM2 is mentioned.
- The demo: 30 seconds of video or 7 slides at most.

**Correction to my PR reviews:** two of my reviews said "GIPOC-locked" was never verified. That was wrong. Part 1 of the team doc verified it: the Saffire IV/V data is on NASA Glenn's GIPOC site, whose page says "Authorized users only".

## 2026-11-14 16:35 PT — Paridhi Singh — Address second RAG review (v4)

- What: Router fix (numbers count only with a unit; PSI IDs and investigation names are meaning questions; highest/lowest numeric only with oxygen/airflow); added max_oxygen()/answer_highest_oxygen() over the full 129 rows (22.2%, 14 ties, number-checked); corrected the Saffire V citation to Urban et al., ICES 2021, Table 1 (NTRS 20210011521), ranges 25.4–26.2% O2 at 70.7–72.6 kPa, 20 cm/s flow; rebuilt material cards from the full CSV (PMMA/other 98, Nomex 3, SIBAL 27, Wax 1) with tied highest-oxygen wording; added exact PSI-ID/name lookup before embeddings; added BASS (PSI-26) and replaced ACME PSI-10 with PSI-20/PSI-21, with a source_notes column per row.
- Why: Daksh's second RAG review on PR #1 asked for all of these before merge, including his correction that the Saffire V numbers come from the ICES 2021 paper, not NASA's challenge notes.
- How: Written with SI assistance (Muse), reviewed by Paridhi Singh. Saffire numbers verified against the NTRS FLARE deck test matrix; ACME BRE/CLD verified against NASA Science investigations page. Tested in the VM (keyword fallback): router, exact lookup, cutoff and max-oxygen answer all pass; embedding ranking of the Saffire-objective and oxygen-sensor questions to be confirmed on the Mac with the real model.
- Check: python3 rag.py, python3 answer.py, python3 cards.py run clean.

### 2026-11-14 16:00 | Paridhi | Revised RAG for Daksh's review: router, text corpus, embedding cache, score cutoff, Saffire V nearest evidence

- What: `logic/rag.py` (router + text corpus + embedding cache + 0.30 score cutoff + source citations), `logic/investigations.csv` (8 investigations), `logic/answer.py` (nearest_evidence field for 30%+ O2), `logic/demo_answers.json` (regenerated, Q1 carries the Saffire V note).
- Why: Daksh's PR #1 RAG review: numeric questions must go to code not embeddings, RAG must read investigation text not the 6 sample rows, off-topic questions must say "no match in our data", and 30% O2 Moon-cabin answers must name Saffire V as nearest evidence.
- How: revised the files with SI assistance (Muse) from the review comments, then ran `python3 rag.py` and `python3 answer.py` in `logic/`.
- Check: router sends highest/lowest/inside questions to code and meaning questions to RAG; smoke-detection question returns SAME with its PSI source; "best pizza topping" returns no match; 30% O2 returns BEYOND with Saffire V (about 26% O2, about 71 kPa) cited to NASA's notes. Saffire V numbers come from NASA's challenge notes per Daksh, not from PSI data.

### 2026-11-14 14:04 | Paridhi | Correction: filename in the first CHRONICLE entry

- What: corrects the first entry (2026-11-14, PSI-25 CSV). The file is `data/raw/PSI-25_Experimental table_BASS-II.csv` — with a space, not underscores.
- Why: the first entry wrote the filename with underscores, which does not match the file in the repo.
- How: this new entry only — the old entry was left untouched, per the CHRONICLE rules.
- Check: `git ls-files data/raw/` lists the file with a space in its name.
- 2026-11-14 Paridhi: Added data/raw/PSI-25_Experimental_table_BASS-II.csv (BASS-II, 129 tests, PSI-25, CC0, DOI 10.60555/4qc4-de67) — raw source, unedited.

### 2026-11-14 13:42 | Paridhi | Added Lane B retrieval (rag.py)

- What: `logic/rag.py` — retrieve() embeds each row as one sentence with sentence-transformers/all-MiniLM-L6-v2 (free, local, no API key) and returns the top 3 rows by cosine similarity; keyword fallback when the model is not installed.
- Why: Lane B — free-text questions need to find the right rows before answer.py builds the answer. Retrieval only: it never writes an answer sentence, so no model output can invent a number.
- How: wrote the file with SI assistance (Muse), installed the model with `pip install sentence-transformers`, then ran `python3 rag.py` in `logic/`.
- Check: ran with the real model — SIBAL question returns T1, T25 on top; Moon-base question returns B1, B2 on top. Known limit: "highest oxygen" ranks T1 (18.5%) above B1/B2 (22.2%) because embeddings do not compare numbers; closest_rows in answer.py is the right tool for highest/lowest questions. Fixed the model re-loading for every question (now cached once per run).

### 2026-11-14 13:01 | Paridhi | Added Lane B material cards (PMMA, Nomex, SIBAL)

- What: `logic/cards.py` — builds one 4-line card per material (what happened / why it matters / next action / what's not known) from `logic/sample_data.csv`, and prints the cards as JSON for the website.
- Why: Lane B — the material cards are the part of the demo a user actually reads, and they have to come from the real rows, never from guessing.
- How: wrote the file with SI assistance (Muse) from the Lane B starter template, then ran `python3 cards.py` in `logic/`.
- Check: ran clean — PMMA (B1, B2, film, 22.2%), Nomex (F1, F2, cloth, 21.0–22.2%), SIBAL (T1, T25, cloth, 18.5–20.8%). Every card states outcome and airflow in cm/s are not in the PSI-25 CSV.

### 2026-11-14 12:37 | Paridhi | Added Lane B logic: classifier, number checker, answer builder, sample data, demo answers

- What: `logic/sample_data.csv` (6 real rows: B1, B2, F1, F2, T1, T25), `logic/classifier.py`, `logic/number_checker.py`, `logic/answer.py`, `logic/demo_answers.json`.
- Why: Lane B — the logic that labels any oxygen / airflow as INSIDE / NEAR / BEYOND what BASS-II tested, answers only from the frozen rows, and flags any number not in the dataset as UNVERIFIED.
- How: wrote the files with SI assistance (Muse) from the Lane B starter, then ran `python3 answer.py` in `logic/`. First committed on main by mistake, then moved to branch `feat/lane-b-agent` and pushed.
- Check: ran clean — 30% O2 → BEYOND, 20% → INSIDE, 24% → NEAR, all number checks ok. Airflow and outcome are blank in the sample on purpose: the PSI-25 CSV has no cm/s column and no outcome column.

### 2026-11-14 09:30 | Daksh | Saved a copy of the PSI-25 table in data/raw

- What: `data/raw/PSI-25_Experimental table_BASS-II.csv` (129 data rows, 17 columns), unedited.
- Why: NASA's PSI file service started returning 504 timeouts, so the download links in the team doc only showed "Redirecting". A copy in the repo keeps the data lane unblocked while PSI is down. The data is CC0 per its PSI record.
- How: the file is the same one downloaded from the PSI download link earlier today, copied without changes. SHA-256: `71e792bf6b5fb5ea620c5dd70fbbac05515992e12aefcf5dff47312caa48c042`. Claude Code did the copy and commit.
- Check: row count 129 and 17 columns match the PSI-25 page. The other seven tables still need to be downloaded once PSI is back, and each needs its SHA-256 recorded the same way.

### 2026-11-14 09:20 | Daksh | Repository created with starting files

- What: `README.md`, `CHRONICLE.md`, `AI_USE_LOG.md`, `.gitignore`, and empty `data/raw/`, `logic/` and `web/` folders.
- Why: give the three lanes (data, logic, app and demo) one shared place to work, and keep a record of every change for the team and for the SI disclosure in the submission.
- How: created the folders and files locally with Claude Code, made the first commit, created the public repository `lost-in-andromedus-flame-in-freefall` under the `dakshvk` GitHub account with the GitHub CLI, then invited the two teammates as collaborators with write access.
- Check: opened the repository page to confirm the files are there.

2026-11-14 | Jenisha (Lane A) | Added data/tests.json (200 rows), experiments.json (24), materials.json, validate.py, review files and notes (data/README_laneA.md) | Clean, sourced test data for the Evidence Map and Explorer; PSI-25 129 rows unchanged; doubtful values flagged, not fixed | Built from the real PSI CSVs, Zhao appendix, BASS-II report, Saffire IV/V and Link 2018 tables; paper rows entered twice and compared; checked by data/scripts/validate.py
