# ArdhiCheck

> Photograph a land survey plan and get a checked report in about a minute: does the paperwork add up, and does the plot sit on land it should not.

Built during the **Meta Global AI Developer Hackathon** (26 Oct – 4 Nov 2026).

---

## Problem

Ordinary buyers in Kenya pay for land on the strength of a survey plan they cannot read. Plans may contain bearings and distances that do not close, stated areas that disagree with the geometry, or mixed datums. Plots may overlap road reserves, riparian buffers or public land. Checking costs KES 50,000–150,000 for a surveyor and advocate; there is nothing cheap that tells a buyer whether the plan is even internally consistent before committing.

ArdhiCheck fills that gap: upload a plan photo, get a checked report in about a minute, and know whether to proceed, walk away, or hire a surveyor—and what to ask them.

## Demo

_Link to 3-minute demo video (to be added before submission)._

## How it works

1. **Snap** – Upload a photo or PDF of the survey plan.
2. **Check** – Muse Spark reads the plan; pure-code geometry tools verify closure, area and datum; SAM 3.1 inspects satellite imagery for rivers, roads and wetlands near the plot.
3. **Decide** – A traffic-light verdict, the specific number that looks wrong, and questions to ask the seller or surveyor.

The model reads and explains; **code calculates**. Every sentence in the report cites the tool output behind it. When the boundary doesn't close, the agent localises the suspect leg, re-reads it from the image, and classifies: AI misread or document inconsistency.

## Meta models used

| Model | Role |
|---|---|
| Muse Spark 1.3 | Plan reading (image + structured output), tool-calling orchestrator, report writer |
| SAM 3.1 | Text-prompted segmentation of rivers, water, roads and buildings in satellite imagery |
| Muse Spark Open (P1) | Independent second extraction for cross-checking |
| Muse Voice Transcribe (P1) | Field dictation of readings |

## Evaluation results

_Results table to be added after the evaluation run._

## Run locally

```bash
# Clone and install
git clone https://github.com/<your-username>/ardhicheck.git
cd ardhicheck
python -m venv .venv
.venv/Scripts/activate      # Windows
# source .venv/bin/activate  # macOS/Linux
pip install -e ".[dev,meta]"

# Set your API key
cp .env.example .env
# Edit .env and add your MODEL_API_KEY

# Run tests and lint
make test
make lint
```

## Built during the hackathon

All code was written between 26 Oct and 4 Nov 2026 during the Meta Global AI Developer Hackathon. An AI coding agent was used for scaffolding and development (see [PROVENANCE.md](PROVENANCE.md)). The repo has been public from the first commit.

The value of ArdhiCheck is the **tool-calling, verification and localisation loop**, not a wrapper around a model. The same design could run on other models; it is built on Meta's models because the hackathon requires it, and because SAM 3.1 plus open-weight Muse models make the cross-checking design possible.

## Limitations

- **Not legal advice.** ArdhiCheck never says a plot is safe to buy. It says what was checked and what was found.
- **Not affiliated with the Ministry of Lands or Ardhisasa.** It does not perform ownership checks or access registry records.
- **Not a replacement for a licensed surveyor.** It helps you decide whether to hire one and what to ask.
- Arc 1960 → WGS84 transforms are accurate to metres only; the app shows an uncertainty note and never claims survey-grade precision.
- Sentinel-2 imagery is 10 m resolution; SAM can find rivers and large water, not small streams or single houses.

## Licences

| Dependency | Licence |
|---|---|
| Python | PSF |
| numpy | BSD-3-Clause |
| pyproj | MIT |
| shapely | BSD-3-Clause |
| pytest | MIT |
| ruff | MIT |
| openai (optional) | Apache-2.0 |
| Sentinel-2 imagery | Copernicus (free and open) |
| Copernicus DEM | Copernicus (free and open) |
| OpenStreetMap | ODbL |
