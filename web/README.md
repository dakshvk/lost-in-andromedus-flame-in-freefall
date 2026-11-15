# Lane C: the website

The page (`index.html`, `css/`, `js/`) and the data layer it reads (`export_data.py`, `js/data.js`, `data/`).

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

## The page

| File | What it does |
|---|---|
| `index.html`, `css/styles.css` | One page: Moon hero with the ask box, answer panel, evidence chart, material cards, ranking, limits drawer, sources. |
| `js/app.js` | Loads the data, wires every section together. |
| `js/moon.js` | The 3D Moon (Three.js, pinned CDN version) with one marker per material; hover for a preview, select for the detail. |
| `js/coverage.js` | The main evidence chart: one row per material on a shared oxygen axis, one tick per test, ending at the empty 30% Moon band. |
| `js/chart.js` | The full oxygen x airflow scatter (behind "Show every test") and each material's own graph. |
| `js/materials.js`, `js/answer.js`, `js/ranking.js`, `js/limits.js`, `js/dom.js` | Cards and material detail, answer panel, ranking, limits drawer, shared helpers. |
| `assets/moon.jpg`, `assets/moon_displacement.jpg` | NASA's Scientific Visualization Studio, CGI Moon Kit (LRO data). Credited on the page. |

Moon style for comparison: add `?moon=nasa` (default), `?moon=procedural`, `?moon=photo` or `?moon=illustration` to the URL. The photo and illustration options use Daksh's inspiration images: the illustration shows an "SI-generated image" label, and the photo needs a source credit before it can be used in the submission.
