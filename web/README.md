# Lane C: website data layer

Design comes later. This folder holds only what the page needs to get its data.

## Run it locally

From the repo root:

```bash
pip install -r requirements.txt
python3 web/export_data.py
uvicorn api.app:app --reload --port 8000
```

Then open http://localhost:8000. The API serves the page from `web/` and the data from `web/data/`.

Re-run `python3 web/export_data.py` whenever Lane A's `data/tests.json` or Lane B's `logic/` changes. Run the tests with `python3 -m pytest -q api logic`.

## Files

| File | What it is |
|---|---|
| `export_data.py` | Builds `web/data/*.json` from Lane A's data through Lane B's code. Nothing typed in by hand except the hardware groups (copied from NASA's challenge notes). |
| `js/data.js` | The page's only data module: `loadTests`, `loadCards`, `loadExperiments`, `loadInvestigations`, `loadLimits`, `ask(question)`, `cardForMaterial`, `pointsForMaterial`, `mapPoints`. Falls back to the static JSON and the saved demo answers when the API is down. |
| `data/tests.json` | 200 tests, one map point each: oxygen, flow start and end, outcome, pressure, flags, citation. |
| `data/cards.json` | 5 standard material cards plus a low-pressure Saffire V group of 3. Counts and ranges skip Link et al. rows and rows with no oxygen, the same rule the answers use. |
| `data/experiments.json` | The 24 ranked PSI investigations with score breakdowns and the "team's judgement" note. |
| `data/investigations.json` | 10 investigations with objective, fuels, conditions, sensors, how they differ, sources, hardware. |
| `data/limits.json` | Every threshold and rule the limits drawer must show, read from the code. |
| `data/demo_answers.json` | Saved answers for the offline fallback. |
| `data/meta.json` | Counts, to check the page against the data. |

## API

| Call | Returns |
|---|---|
| `GET /api/health` | `{ok, rows, total_tests, data_exported}` |
| `POST /api/ask` with `{"question": "..."}` | Lane B's answer: `path` (`code` or `rag`), `answer` (verdict, sentence, evidence, nearest_evidence, unknown, gravity_note, sources, number_check) or `retrieval` (match, results), plus `material` (the material named in the question, or null). Questions are limited to 300 characters. |
| `GET /api/data/{name}` | One of the files above, by name without `.json`. |
