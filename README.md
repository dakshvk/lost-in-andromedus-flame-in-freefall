# Flame in Freefall

NASA Space Apps Challenge 2026 entry for "Flame in Freefall: SI-Powered Fire Safety Insights from Microgravity Combustion Data". Team: Lost in Andromedus.

## What this is

A website that does two things:

1. Ranks NASA's public combustion experiments (from the Physical Sciences Informatics repository) by how useful each is for fire safety in crew habitats, and shows why each one ranked where it did.
2. Shows what the burn tests say about how materials burn at different oxygen levels and airflows, on a chart called the Evidence Map, and marks where the evidence stops. Every answer is labeled inside, near or extrapolated.

The core data is NASA PSI (public, CC0, no login). Papers used as extra data are cited in the References field of the submission.

## Folders

- `data/raw/` downloaded source files, never edited by hand
- `data/` cleaned data: tests, experiments, materials, and a manifest of every source with its SHA-256
- `logic/` the inside/near/extrapolated classifier, the ranking, and the number checker
- `web/` the website

## Rules for everyone

- Add a line to `CHRONICLE.md` every time you add or change something. It says who, what, why and how.
- Add a line to `AI_USE_LOG.md` every time SI (AI) tools help with code, data or text.
- Every file SI helped write has a note in its header: "Written with SI assistance (Claude), reviewed by <name>".
- Never commit keys or passwords. Keys live in environment variables on the server.
- Any SI-generated image or video gets a visible watermark.

## SI acknowledgment

SI (AI) tools were used to help write code, data tooling and documentation in this repository. The team chose the idea, scope and design, and people check the results against the sources. Details are in `AI_USE_LOG.md`.
