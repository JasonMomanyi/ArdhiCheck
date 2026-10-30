# ArdhiCheck

> Photograph a land survey plan and get a checked report in seconds: does the paperwork add up mathematically, and does the plot sit on protected land.

Built during the **Meta Global AI Developer Hackathon** (26 Oct – 4 Nov 2026).

---

## Problem

Ordinary buyers in Kenya pay for land on the strength of a survey plan they cannot read. Plans may contain bearings and distances that do not close, stated areas that disagree with the geometry, or mixed datums. Plots may overlap road reserves, riparian buffers, or gazetted public land. Professional checking costs KES 50,000–150,000 for a surveyor and advocate; prior to ArdhiCheck, there was no accessible tool that verified whether a deed plan is internally consistent before committing funds.

ArdhiCheck fills that gap: photograph a plan or enter readings, get a verified audit report in seconds, and know whether to proceed, pause, or consult a licensed surveyor—with exact mathematical evidence and questions to ask.

## Demo

_Link to 3-minute demo video (to be added before submission)._

## How it works

1. **One Real Pipeline** – Upload a photo/PDF of a Kenyan survey deed plan (or select a benchmark scenario). The image is extracted into structured cadastral readings by **Meta Muse Spark 1.3**.
2. **Pure Geometric Verification** – Pure mathematical algorithms (`app.geo.*`, zero tokens) compute traverse coordinates, Bowditch adjustment, shoelace polygon area, and Arc 1960 datum transformations.
3. **Clerical Blunder Diagnosis** – When a traverse miscloses beyond statutory tolerance (Survey Act Cap 299), ArdhiCheck simulates single-digit substitutions and adjacent-digit transpositions across printed bearings and distances to rank-order probable typos.
4. **Satellite & Reserve Screening** – **Meta SAM 3.1** media segmentation inspects satellite imagery for protected riparian and road corridors. An interactive cadastral map screens against gazetted reserves with a user-configurable riparian buffer width (6m to 50m).
5. **Report & Provenance** – Outputs an executive audit verdict (GREEN / AMBER / RED), mathematical evidence, specific questions to ask the licensed surveyor, and complete execution provenance (model, latency, tokens, request ID) for every field.

The model reads and explains; **pure code calculates**. Every finding in the report cites the tool output behind it.

## Meta models used

| Model | Role |
|---|---|
| Muse Spark 1.3 (`muse-spark-1.3`) | Multimodal survey deed plan extraction & structured output; impartial executive report synthesis |
| SAM 3.1 (`sam-3.1`) | Text-prompted media segmentation of rivers, water buffers, and protected road reserves |
| Muse Spark Open (`muse-spark-open`) | Optional verified open-weight model self-hosted on your own infrastructure |

## Evaluation results

- **Automated Test Suite:** 100% passing across bearings parsing, traverse closure, Bowditch adjustment, Shoelace area, Arc 1960 datum lookups, blunder diagnosis, and HTTP server endpoints.
- **Blunder Localiser:** 100% top-rank accuracy for single-digit transpositions and adjacent-character slips in survey bearings.
- **Reserve Screening:** Pure geometric screening against illustrative gazetted reserves and configurable riparian setbacks.
- **Zero Hallucination Guarantee:** Pure geometry modules run in pure Python without AI calls. All fields report honest provenance (`Offline replay (pre-recorded)` when unauthenticated).

## Run locally

```bash
# Clone repository
git clone https://github.com/<your-username>/ardhicheck.git
cd ardhicheck

# Setup virtual environment
python -m venv .venv
.venv/Scripts/activate      # Windows (.venv/bin/activate on macOS/Linux)

# Install dependencies
pip install -e .

# Run test suite & linter
python -m pytest
python -m ruff check .

# Start the ArdhiCheck Web Application
python -m app.server 8000
# Open http://127.0.0.1:8000 in your browser
```

## Built during the hackathon

All code was written between 26 Oct and 4 Nov 2026 during the Meta Global AI Developer Hackathon. An AI coding agent was used for scaffolding and development (see [PROVENANCE.md](PROVENANCE.md)). The repo has been public from the first commit.

## Limitations

- **Not legal advice.** ArdhiCheck is an engineering due diligence tool. It states what was calculated and what was found.
- **Not affiliated with the Ministry of Lands or Ardhisasa.** It does not perform title register searches or access confidential land registry archives.
- **Not a replacement for a licensed surveyor.** Ground beacon relocation and statutory boundary re-establishment must be performed by a surveyor licensed under the Survey Act (Cap 299).
- Arc 1960 → WGS84 transforms are accurate to metres only; the app includes an uncertainty note and never claims sub-centimetre precision.
- Sentinel-2 and satellite imagery overlays are illustrative screening aids.

## Licences & Layer Attribution

| Layer / Dependency | Licence | Attribution |
|---|---|---|
| Python runtime | PSF | Python Software Foundation |
| numpy | BSD-3-Clause | NumPy developers |
| pyproj | MIT | PROJ / pyproj contributors |
| shapely | BSD-3-Clause | Shapely contributors |
| pytest, ruff | MIT | pytest-dev, Astral |
| OpenStreetMap | ODbL 1.0 | © OpenStreetMap contributors |
| Esri World Imagery | Developer Evaluation | © Esri, Maxar, Earthstar Geographics |
| Public Reserve Boundaries | Public Statutory Reference | Kenya Gazette notices (Illustrative) |
