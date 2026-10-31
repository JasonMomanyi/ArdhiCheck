# ArdhiCheck – Meta Hackathon Demo Video Script

**Target Duration:** ~3 minutes (under 5 minutes)
**Video File:** `recordings/ardhicheck_demo_walkthrough.webp`
**Event:** Meta Global AI Developer Hackathon (Oct 26 – Nov 4, 2026)

---

### [0:00 - 0:25] The Problem & Introduction
> **Visual:** Homepage, Header with *Meta Hackathon 2026* badge, honest telemetry banner.
>
> **Narration:**
> "Welcome to **ArdhiCheck**, the AI-powered Kenyan cadastral land due-diligence engine
> built for the Meta Global AI Developer Hackathon.
> In Kenya, land fraud and clerical blunders in survey plans cost buyers and financial
> institutions billions of shillings. Deeds often contain transposed bearings, unclosed
> traverses, or overlap gazetted public forests and riparian river reserves.
> ArdhiCheck solves this with a mathematically rigorous, dual-engine approach:
> Meta Muse AI for multimodal document extraction and computer vision, combined
> with pure geometric verification under Kenya's Survey Act Cap 299."

---

### [0:25 - 0:50] Hackathon Models & Cerebral Valley Failover
> **Visual:** Opens Meta Model API Configuration modal showing official `muse-spark-1.3`,
> `muse-spark-open`, `muse-glimmer`, and `sam-3.1`.
>
> **Narration:**
> "ArdhiCheck runs on Meta's official **Muse Spark 1.3** via the Meta Model API at `dev.meta.ai`.
> In accordance with Cerebral Valley's hackathon guidelines, we also support Meta open-weight
> models—including **Muse Spark Open**, **Muse Glimmer**, and **SAM 3.1** on self-hosted compute.
> Every result features honest, auditable telemetry with exact token usage, model IDs,
> and latencies—and pure geometry never fabricates AI calls."

---

### [0:50 - 1:30] Real Cadastral Pipeline (Scenario 1: Clean Deed Plan)
> **Visual:** Clicks *Scenario 1: Nairobi Upper Hill*. Green verdict banner, relative
> precision 1:inf, Bowditch canvas, shoelace area, and execution provenance cards.
>
> **Narration:**
> "Here is our single real pipeline in action.
> We send a deed plan for L.R. 209/14682 in Upper Hill, Nairobi.
> Meta Muse Spark 1.3 extracts the boundary schedule in seconds.
> Our pure Python geometry engine runs Bowditch closure and Shoelace area calculation.
> The traverse closes with zero linear error, the statutory area matches 0.50 hectares
> exactly, and the parcel is certified **GREEN**."

---

### [1:30 - 2:05] Algorithmic Blunder Localization (Scenario 2: Typo Detected)
> **Visual:** Clicks *Scenario 2: Nakuru Municipality*. Amber verdict banner, 62.4m linear
> misclosure. Candidate Typo Fixes table highlighting `Leg 2: 009° -> 090°`.
>
> **Narration:**
> "Now, look what happens with a common human error. In this Nakuru residential plot,
> the deed plan printed `009°` instead of `090°`—a clerical transposition.
> The traverse fails closure with over 62 meters of linear error.
> But ArdhiCheck's algorithmic typo ranker tests adjacent-digit transpositions and
> single-digit substitutions. Within milliseconds, it localizes the exact blunder to Leg 2,
> ranking the true fix at #1 with a single click."

---

### [2:05 - 2:35] Universal Document & GIS Upload
> **Visual:** Upload card with drag & drop for images, PDFs, CSV coordinate tables,
> and GeoJSON boundaries, plus the *Download Test Pack (.zip)* button.
>
> **Narration:**
> "Users and evaluators don't need to manually type coordinates. ArdhiCheck accepts photos,
> scans, PDFs, CSV coordinate tables, and GeoJSON boundary polygons.
> Evaluators can also download our complete Kenyan test survey pack directly from the dashboard."

---

### [2:35 - 3:00] Inbuilt Interactive Kenya Map & Spatial Reserve Screening
> **Visual:** Switches to *Cadastral Map & Spatial Reserve Screening*. Clicks points on
> Nairobi map, draws polygon, adjusts riparian buffer slider to 45m.
> Then clicks inside Karura Forest to show red conflict warning.
>
> **Narration:**
> "Finally, our spatial reserve screening engine screens land parcels against Kenya's
> gazetted public forests, Nairobi National Park, and statutory river corridors.
> Users can drop boundary beacons on the interactive map, adjust environmental riparian
> buffer setbacks dynamically, and immediately know if a parcel infringes on public land.
>
> **ArdhiCheck: Turning cadastral uncertainty into verified certainty with Meta AI.**"
