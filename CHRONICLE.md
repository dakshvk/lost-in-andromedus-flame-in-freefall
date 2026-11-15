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
