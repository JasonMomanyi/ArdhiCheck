# ArdhiCheck – Provenance

## Project timeline

- **Start date:** 26 October 2026 (Meta Global AI Developer Hackathon kickoff)
- **End date:** 4 November 2026
- All code in this repository is new work written during the hackathon.

## AI coding tools

An AI coding agent was used for scaffolding, code generation, and development assistance throughout the project. All generated code was reviewed and tested by the author.

## Third-party libraries and their licences

| Library | Version | Licence | Purpose |
|---|---|---|---|
| numpy | >=1.24 | BSD-3-Clause | Numerical computation & coordinate arrays |
| pyproj | >=3.6 | MIT | Coordinate reference system transforms (Arc 1960 / UTM 37S) |
| shapely | >=2.0 | BSD-3-Clause | Geometric operations & spatial reserve screening |
| httpx | >=0.25 | BSD-3-Clause | HTTP client for Meta Model API endpoints |
| pillow | >=10.0 | HPND | Survey plan and satellite raster generation |
| pytest | >=7.0 | MIT | Automated test framework (dev) |
| ruff | >=0.4 | MIT | Code quality & formatting (dev) |

## Sample Documents and Data Rights

All cadastral survey diagrams, deed plan images, and sample documents in this repository are synthetic test fixtures or authorized demonstration materials. The author holds explicit rights and consent to use any sample documents for technical verification testing; use is fully authorized and complies with data protection guidelines. No confidential, proprietary, or unauthorized private land registry records are exposed. Any sample or demonstration documents used during model testing have all personal identifiers, crucial owner details, and sensitive attributes redacted or blurred to protect personal privacy. Demonstration satellite clips and survey deed plans were synthetically generated to test edge cases (riparian setbacks, clerical blunders, and clean closures).

## Pre-existing code

No code was copied from any prior project. Domain principles from the author's background were applied, but all implementation is original work written during the hackathon.
