# Lane A: data notes (tests.json, materials.json)

**Counts (checked by `validate.py`):** 200 rows = psi-25 129, paper-link2018 52, psi-99 10, paper-saffire45 5, psi-98 2, psi-100 2.
Every row has a citation. Paper rows are `hand_entered` and were read twice (script vs by eye); they agree.
`materials.json` is computed by `build_materials.py`. Link 2018 rows are not counted in outcomes (all are "burning with a spread rate").

## Known issues (flagged, not silently fixed)
- **Link 2018 spread-rate unit unresolved.** Table S1 header says cm/s on the left half and mm/s on the right half. Likely a typo, unconfirmed. Values stored as printed.
- **Link vs PSI-25 flow calibration differs** (e.g. P17: Link Vg 1.01, 0.82, 0.41 vs PSI-25 Air display "5 3 2 22 2 low"). Do not mix the two flow scales without noting it.
- **O2 uncertainty about +/-0.3%** (Link Fig. 7 caption).
- **GMT190-T24 width conflict:** PSI-25 and BASS-II say 1 cm, Zhao appendix says 2.2 cm. Both recorded in the row.
- **GMT213-O10:** the report gives GMT 203, PSI-25 gives 213 (typo in one of them). Kept as PSI-25.
- **B5:** report note questions a raw O2 reading (`o2_reading_questioned`).
- **o2_end_suspect:** B2, P22a, P22b, T28a, T28b.
- **SIBAL unknowns T5, T6, T11, T16, T19:** report notes could possibly fill them, but kept `unknown` (no guessing).
- **Saffire IV/V and Saffire II (PSI-99) conflict with ICES-2021-266 Table 2** on some oxygen/flow values. Noted in rows, not reconciled. Saffire never-ignited samples are not entered.
- **PSI-98/99/100 oddities:** thickness header says cm but values look like mm; PSI-99 2-6 and 2-9 have blank material (filled from context, noted in the row); 2-7 PMMA & Nomex split into two rows; PSI-100 has no O2 or outcome so rows are `context_only`; PSI-99 1-g columns kept as raw fields only.
- **Judgement calls:** 13 PSI-25 labels in `review_needed.csv`, 4 silicone labels in `review_saffire123.csv`. Defaults were Claude's suggestions accepted by the Lane A owner on 2026-11-14; second-person check pending.

## Still open (team decisions)
- Low-flow cutoff for `low_flow_uncertain` (not applied yet).
- Which flow the map plots for SIBAL (PSI-25 vs Zhao; both stored).
- `experiments.json` needs the PSI combustion catalog list.
- No label changes after the freeze except real errors; tell Lane B and C when labels change.

## experiments.json (24 experiments)
Built from the pasted PSI search page. The page said "1 - 25 of 26": 25 shown, 25th-26th result (page 2) not seen. Two of the 25 are not combustion (PSI-181 Materials Science solders, PSI-108 Fluid Physics STDCE-1) and were left out, so 23 are in. PSI-47 (DAFT) is named in the plan but was not on page 1: probably the missing result, unconfirmed.
Copied from the page: id, title, research area, project type. Ours (judgement): fuel_type, one-sentence summary. test_count only for PSI-25/98/99/100 (counted from our tables); others null. has_data_table true only for ids the plan lists; others null (not checked). url uses the page pattern psi.nasa.gov/physci/repo/data/investigations/PSI-xx (copied from the PSI-47 link supplied by the Lane A owner; not opened for each id); the JSON record link is kept in url_record_json. Scores left blank for Lane B.

Update 17:50: PSI-47 (DAFT/DAFT-2) added from the owner's screenshot of its page (Combustion Science, sub-area Spacecraft Fire Safety, microgravity, ISS). It was not on search page 1, so it is probably the 26th result (page 2 not seen; unconfirmed). sub_research_area is known only for PSI-47; other rows are null (not checked).

Pages applied so far (pasted page text): PSI-47 (screenshot), 117, 159, 10, 62, 60, 142, 101, 115. PSI-181 (Materials Science) and PSI-108 (Fluid Physics) were also pasted; their pages confirm they are not combustion, so they stay out of experiments.json. Test counts from PSI pages are the page's own "1 - 5 of N" and were not counted by us (PSI-142's 9 is a data summary table, PSI-101's 110 differs from the page's "66 test points").

Update 18:15: pages applied also for PSI-98, 99, 100, 39, 102, 106, 107 (sub-area known for 15 of 24; PSI-106 page read but blank). Notes:
- **PSI-99 flow conflict (not reconciled):** the PSI-99 page says Saffire-II ran at 20 or 30 cm/s depending on the sample material, but the PSI-99 table lists 20 cm/s for every row. Our rows keep the table's value.
- PSI-98 page confirms Saffire-I ran at 20 cm/s. PSI-100 page confirms 30 cm/s (the ICES-2021-266 paper says 25 cm/s for one Saffire III test; see row notes).
- Sub-area wording differs by page ("Spacecraft Fire Safety", "Spacecraft Fire, Smoke Distribution", "Fire Safety", "Surface Combustion", ...). Stored as written; Lane B must decide which count as "spacecraft fire safety" for the +3.
- PSI-106 leaves sub-area blank; PSI-107's table tab is empty (0 of 0).
- Page counts like "1 - 5 of 16" can include note and camera lines (PSI-99), so they are not always test counts.

Update 18:20: pages applied for PSI-21, 25, 20, 68, 22, 23, 69, 26 too. Sub-area is now known for 23 of 24 (only PSI-106 is blank on its own page); every experiment's summary now rests on the full page text. Notes:
- PSI-25's page table count is 130; our CSV has 129 data rows (page count includes one extra line). PSI-25's test_count stays 129 (counted by us).
- PSI-21, 20, 22, 23 tables are day-by-day summaries (flames ignited per day), not single burns. Their counts are the page's table length, not tests.
- PSI-26 page count 123 (plan expects 122 rows). Not counted by us because no PSI-26 CSV was supplied.
- OPEN: the plan lists PSI-20 (ACME BRE, 18 rows) and PSI-26 (122 rows, 6 columns) tables as `context_only` rows and "psi-20" is an allowed source, but no PSI-20 or PSI-26 CSV was sent, so tests.json has no rows from them. Say if the team wants them added.

Update 18:30: PSI-26 and PSI-20 CSVs received. Rows built by `build_context_rows.py` into `data/tests_context_only.json` (121 PSI-26 rows + 18 PSI-20 rows, all `context_only`, no oxygen/airflow/outcome). **NOT merged into tests.json**, because "psi-26" is not an allowed source in the contract and the freeze has passed; merging adds 139 rows and changes counts for Lane B and C. The team must say yes first (then: add psi-26 to the allowed sources everywhere and run `build_tests.py` with the file appended).
- PSI-26: 122 table lines = 121 tests + 1 "SOOT Cleaning" line (8/3/2012, not a test, left out). Counts match the plan (122) and the PSI page (123 = +1).
- PSI-26 material: "2 cm sphere" / "1 cm sphere" cells do not say the material. PMMA was taken only where another row of the same sample # says PMMA (sample 21, 22, 25, 26). Samples 16, 18, 20 (11 rows) are `other` with the reason in flow_note. Not inferred.
- PSI-26 typos kept as printed: date "5/15/2103", date "6/29/`12", GMT 113 on 4/26/2013, GMT 137 on 6/1/2013, and duplicate "Test # 114" (different GMT, so ids stay unique).
- PSI-20: 18 rows are test-day summaries (flames ignited that day), oxygen listed as text like "21; 26.5; 40"; two cells read "3400%" and "2100%" (probably typos), kept as printed. Material is `other` (gas burner imitating a solid).
- experiments.json test_count for PSI-26 (122) and PSI-20 (18) now comes from our own CSVs.

Update 18:35: PSI-21 CSV received: 32 test-day summary rows (page shows 33, one more). Used only for experiments.json test_count; no rows built (not in the plan's list of row sources; it is a day summary with no oxygen, airflow or outcome). Its "Fuel Bottle" column reads like "40% CH5, 40% CH6, ..." (looks like bottle numbering, probably not real fuel names); kept raw, not interpreted.

Update 18:40: PSI-47 CSV received: 2 sessions (D1 GMT 54 2005, D2 GMT 63 2005) testing aerosol instruments with Arizona Road Dust. Not burns, no rows built. experiments.json test_count for PSI-47 = 2 (our CSV). All 8 table CSVs in the plan are now received.

## Team decisions, 2026-11-14 (Daksh's check)
- Low-flow cutoff: `low_flow_uncertain` is set when flow_start or flow_end is under 2 cm/s. The BASS-II report says low flows have "high error bars" but gives no number, so 2 cm/s is a team choice (set in build_tests.py as LOW_FLOW_CM_S; show it in the limits drawer). 54 rows carry the flag.
- SIBAL flow on the map: use the PSI-25 value (same scale as PMMA); show Zhao's flow in the tooltip (stored in flow_note).
- Context-only rows (PSI-26, PSI-20): NOT merged into tests.json. They stay in tests_context_only.json for test counts and the compare view.
- Flow fixes: O5b flow_start 49 -> 5 (49 was the fan reading; "49 5 cm/s", pot 1.3 = 5 cm/s). O13a flow 49 -> 5, flow_end 0 (bracket "5 2 0").
- Rule for "flow turned off, then flame went out": that is an operator action, not a quench, so the outcome is `unknown`. Applied to B1, P6, P13a, P5, M17 (B1 changed from quenched to unknown). P13b stays quenched (flame went out with the pot still at 0.32).
- Blind check of 20 rows by Daksh: all 20 matched (18 quenched, 2 burning; blow-off, no ignition and unknown were not in the sample). His file is blind_check_20_daksh.csv.
