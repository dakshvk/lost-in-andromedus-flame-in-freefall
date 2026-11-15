# Lane A scripts
Written with SI assistance (Claude), reviewed by <fill in name>.
- `validate.py`: checks tests.json (counts, citations, allowed values). Run: `python3 validate.py` (needs only data/tests.json). Must print OK before every deploy.
- `build_materials.py`: recomputes materials.json from tests.json.
- `build_*.py`, `extract_bass2_notes.py`, `apply_pages.py`, `pages_data.py`: the code that built the data. Rebuilding needs the source PDFs (Zhao, BASS-II report, Saffire IV/V, Link) in data/raw/. Those big PDFs are not in the repo; their SHA-256 is in data/manifest.json.
