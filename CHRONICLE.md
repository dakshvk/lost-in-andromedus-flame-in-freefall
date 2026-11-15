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

- 2026-11-14 Paridhi: Added data/raw/PSI-25_Experimental_table_BASS-II.csv (BASS-II, 129 tests, PSI-25, CC0, DOI 10.60555/4qc4-de67) — raw source, unedited.

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
