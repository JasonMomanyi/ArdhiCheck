# ArdhiCheck Cadastral Verification Benchmark

Deterministic evaluation of the **pure Python statutory geometry engine** (`app.geo.*`) across **20 synthetic Kenyan cadastral benchmark plans** with verified ground truths.

> [!NOTE]
> This benchmark measures mathematical and algorithmic verification on known ground-truth traverse schedules. It validates floating-point Bowditch traverse closure, shoelace polygon area calculation, and combinatorial clerical typo diagnosis without external LLM token expenditure.

---

## 1. Measured Performance Metrics

| Evaluation Dimension | Measured Result | Specification / Methodology |
|---|---|---|
| **Traffic-Light Verdict Accuracy** | **95.0%** (19/20) | Illustrative statutory thresholds (GREEN, AMBER, RED) |
| **Traverse Closure Accuracy (Bowditch)** | **100.0%** (20/20) | Strict agreement with known mathematical closure (< 0.05 m tolerance) |
| **Area Discrepancy Detection** | **100.0%** (5/5 deficit cases detected) | Exact shoelace polygon area vs stated title acreage (> 3% threshold) |
| **Blunder Localisation (Rank-1 Typo)** | **60.0%** (3/5) | Combinatorial single-digit substitution and transposition ranker |
| **Tokens Consumed for Geometry** | **0 tokens** | Computed in pure Python floating-point math at zero inference cost |
| **Average Geometry Latency** | **2.82 ms** | Local arithmetic execution per survey plan |

---

## 2. Key Architecture Principles

1. **Deterministic Separation of Concerns**:
   - Probabilistic language models are well suited for perceptual parsing (extracting printed coordinates from scanned images), but ill-suited for strict trigonometry.
   - ArdhiCheck routes all bearing arithmetic, Bowditch coordinate adjustments, and polygon closures directly to pure Python functions (`app.geo.traverse`), ensuring zero hallucination risk in legal due diligence calculations.

2. **Area Inflation Screening**:
   - In fraudulent title transactions, documents may state inflated acreage (e.g., stating 0.85 ha when boundary coordinates enclose only 0.50 ha).
   - The geometry engine independently computes parcel area from traverse coordinates and flags discrepancies exceeding illustrative statutory thresholds.

3. **Clerical Blunder Diagnosis**:
   - When a survey plan miscloses due to a single-digit clerical error (e.g., typing `009°` instead of `090°`), ArdhiCheck simulates single-digit substitutions and adjacent-digit transpositions across printed bearings and distances, successfully isolating the faulty leg and value in **60%** of single-blunder cases at Rank 1.

---

## 3. Case-by-Case Benchmark Results (20 Plans)

| Case ID | Category | Parcel Identifier | Expected Verdict | Measured Verdict | Computed Misclosure | Computed Area | Latency |
|---|---|---|---|---|---|---|---|
| `EVAL-C1` | Clean Cadastral Traverse | `L.R. 209/5001` | **GREEN** | **GREEN** | 0.000 m | 5000.0 m² | 0.09 ms |
| `EVAL-C2` | Clean Cadastral Traverse | `L.R. 11942/10` | **GREEN** | **GREEN** | 0.000 m | 6400.0 m² | 0.07 ms |
| `EVAL-C3` | Clean Cadastral Traverse | `L.R. 8421/101` | **GREEN** | **GREEN** | 0.000 m | 6235.4 m² | 0.06 ms |
| `EVAL-C4` | Clean Cadastral Traverse | `L.R. 3777/202` | **GREEN** | **GREEN** | 0.000 m | 3600.0 m² | 0.07 ms |
| `EVAL-C5` | Clean Cadastral Traverse | `L.R. 15430/4` | **GREEN** | **GREEN** | 0.000 m | 6000.0 m² | 0.09 ms |
| `EVAL-B1` | Clerical Typo / Blunder | `L.R. 8421/39` | **AMBER** | **AMBER** | 64.945 m | 2891.1 m² | 6.09 ms |
| `EVAL-B2` | Clerical Typo / Blunder | `L.R. 209/7712` | **AMBER** | **AMBER** | 72.000 m | 2683.9 m² | 6.13 ms |
| `EVAL-B3` | Clerical Typo / Blunder | `L.R. 9102/44` | **AMBER** | **AMBER** | 120.000 m | 4156.9 m² | 4.70 ms |
| `EVAL-B4` | Clerical Typo / Blunder | `L.R. 6512/12` | **AMBER** | **AMBER** | 10.000 m | 3888.0 m² | 5.41 ms |
| `EVAL-B5` | Clerical Typo / Blunder | `L.R. 1420/8` | **AMBER** | **AMBER** | 78.785 m | 180.9 m² | 6.09 ms |
| `EVAL-G1` | Gross Traverse Misclosure | `L.R. 4001/1` | **RED** | **RED** | 64.031 m | 5483.9 m² | 5.73 ms |
| `EVAL-G2` | Gross Traverse Misclosure | `L.R. 4001/2` | **RED** | **RED** | 53.852 m | 4524.1 m² | 5.61 ms |
| `EVAL-G3` | Gross Traverse Misclosure | `L.R. 4001/3` | **RED** | **RED** | 26.458 m | 4525.7 m² | 4.28 ms |
| `EVAL-G4` | Gross Traverse Misclosure | `L.R. 4001/4` | **RED** | **AMBER** | 25.000 m | 3939.2 m² | 6.24 ms |
| `EVAL-G5` | Gross Traverse Misclosure | `L.R. 4001/5` | **RED** | **RED** | 61.033 m | 6913.0 m² | 5.44 ms |
| `EVAL-A1` | Stated Area Deficit | `L.R. 7001/1` | **RED** | **RED** | 0.000 m | 5000.0 m² | 0.06 ms |
| `EVAL-A2` | Stated Area Deficit | `L.R. 7001/2` | **RED** | **RED** | 0.000 m | 3200.0 m² | 0.06 ms |
| `EVAL-A3` | Stated Area Deficit | `L.R. 7001/3` | **RED** | **RED** | 0.000 m | 3600.0 m² | 0.06 ms |
| `EVAL-A4` | Stated Area Deficit | `L.R. 7001/4` | **RED** | **RED** | 0.000 m | 6000.0 m² | 0.10 ms |
| `EVAL-A5` | Stated Area Deficit | `L.R. 7001/5` | **RED** | **RED** | 0.000 m | 4900.0 m² | 0.10 ms |

---

## 4. Reproducibility & Governance

- **Execution Command**: `python -m eval.run_eval`
- **Audit Logging**: Every benchmark run records exact linear misclosures, shoelace areas, and candidate typo fixes.
- **Illustrative Standards Disclaimer**: Statutory tolerances (1:5,000 relative precision, 0.30m linear tolerance, 3% area difference, and 30m riparian setback) represent illustrative engineering defaults to be verified by a licensed land surveyor.
