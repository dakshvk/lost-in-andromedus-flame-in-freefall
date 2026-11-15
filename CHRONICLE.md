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

2026-11-14 | Jenisha (Lane A) | Added data/tests.json (200 rows), experiments.json (24), materials.json, validate.py, review files and notes (data/README_laneA.md) | Clean, sourced test data for the Evidence Map and Explorer; PSI-25 129 rows unchanged; doubtful values flagged, not fixed | Built from the real PSI CSVs, Zhao appendix, BASS-II report, Saffire IV/V and Link 2018 tables; paper rows entered twice and compared; checked by data/scripts/validate.py
