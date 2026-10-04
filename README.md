# Place Review Intelligence

Place Review Intelligence turns restaurant review data, restaurant profiles, menus, management observations, and structured market evidence into numerical analysis, topic-level sentiment findings, competitive benchmarks, actions, and management presentations.

The current primary business is **Al Assiel Restaurant & Shisha, Bonn, Germany**. Phase 1 is complete and ready for management presentation, implementation, and measurement.

# ⭐ Most Important Files

| Start here | Location |
| --- | --- |
| English Manager Package | [`final_manager_package/english/`](final_manager_package/english/) |
| German Manager Package | [`final_manager_package/deutsch/`](final_manager_package/deutsch/) |
| English Internal Management PDF | [`01_Al_Assiel_Management_Review.pdf`](final_manager_package/english/01_Al_Assiel_Management_Review.pdf) |
| English Competitive PDF | [`02_Al_Assiel_Competitive_Intelligence.pdf`](final_manager_package/english/02_Al_Assiel_Competitive_Intelligence.pdf) |
| German Management PDF | [`01_Al_Assiel_Managementbericht.pdf`](final_manager_package/deutsch/01_Al_Assiel_Managementbericht.pdf) |
| German Competitive PDF | [`02_Al_Assiel_Wettbewerbsanalyse.pdf`](final_manager_package/deutsch/02_Al_Assiel_Wettbewerbsanalyse.pdf) |
| Project Map | [`docs/02_PROJECT_MAP.md`](docs/02_PROJECT_MAP.md) |
| How to Run | [`docs/03_HOW_TO_RUN.md`](docs/03_HOW_TO_RUN.md) |
| Project Overview | [`docs/01_PROJECT_OVERVIEW.md`](docs/01_PROJECT_OVERVIEW.md) |

# Project Status

**Phase 1 — Complete**

Validated deliverables include the internal Al Assiel analysis, three-competitor analysis, English and German management reports, and automated analytical and presentation QA. The next stage is to choose 3–5 actions, assign owners and KPIs, implement them, then measure the result.

# Restaurants Covered

| Restaurant | Role | Stored reviews |
| --- | --- | ---: |
| Al Assiel | Primary business | 298 |
| Olivenzweig | Formal competitor | 718 |
| Al Safa | Formal competitor | 2,696 |
| Beit Fayrouz | Formal competitor | 82 |

Al Assiel has 220 written reviews, a Google rating of 4.5, and a collected average rating of approximately 4.483221.

# Pipeline

```text
Collection → Preparation → Numerical Analysis → Text Analysis → Reporting
                                                        ↓
                                              Competitive Analysis
                                                        ↓
                                           Management Presentations
```

The five layers live in [`src/`](src/). Competitive Analysis is a separate cross-restaurant analysis, not “Layer 06.” The persistent restaurant data lives in [`businesses/restaurants/`](businesses/restaurants/), and generated results live in [`output/`](output/).

# Quick Start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python run_all.py
```

`run_all.py` uses stored reviews and runs Layers 02–05. It does **not** run paid/external collection unless collection is explicitly requested. See [How to Run](docs/03_HOW_TO_RUN.md) before refreshing reviews or rebuilding presentations.

Run the test suite with:

```bash
.venv/bin/python -m unittest discover -s tests -v
```

# Final Deliverables

Use [`final_manager_package/`](final_manager_package/) for files intended for presentation or sharing. The unchanged generated source package remains in [`output/final_manager_package/`](output/final_manager_package/).

Recommended order:

1. Internal Management Review / Managementbericht
2. Competitive Intelligence / Wettbewerbsanalyse
3. Agree on priority actions, owner, deadline, and KPI

# Security Note

`.env` contains local credentials and must not be committed. `.env.example` contains placeholders only. Review databases and outputs may contain source metadata; use an appropriately private repository and avoid exposing reviewer information unnecessarily.

## Documentation

1. [Project Overview](docs/01_PROJECT_OVERVIEW.md) — purpose, scope, and Phase 1 status.
2. [Project Map](docs/02_PROJECT_MAP.md) — quickest route to every major part of the repository.
3. [How to Run](docs/03_HOW_TO_RUN.md) — setup, analysis, collection, testing, and presentation commands.
4. [Data and Databases](docs/04_DATA_AND_DATABASES.md) — restaurant isolation, paths, inputs, and outputs.
5. [Analysis Method](docs/05_ANALYSIS_METHOD.md) — layers, periods, evidence thresholds, and guardrails.
6. [Presentations](docs/06_PRESENTATIONS.md) — final PDFs, source builders, and localization.
7. [Management Workflow](docs/07_MANAGEMENT_WORKFLOW.md) — how to use the findings and measure action.
8. [Future Development](docs/08_FUTURE_DEVELOPMENT.md) — unimplemented opportunities, including POS integration.
