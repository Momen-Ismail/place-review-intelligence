# How to Run

Run commands from the repository root.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Add credentials only to `.env`. It is ignored by Git; do not put secrets in `.env.example`.

## Scenario A — Normal Analysis Using Stored Reviews

For the default Al Assiel analysis:

```bash
python run_all.py
```

This is the normal entry point. It runs Layers 02–05 in order and uses the existing database. **Layer 01 is excluded unless `--include-collection` is explicitly supplied.**

The active restaurant defaults to `al_assiel`. [`config.py`](../config.py) supports selecting another isolated restaurant through the `BUSINESS_NAME` environment variable, for example:

```bash
BUSINESS_NAME=olivenzweig python run_all.py
```

## Scenario B — Collect New Reviews

Collection is separate because it may invoke Apify, contact an external service, and cost money. Inspect the target restaurant and its existing database before running it.

The Layer 01 command is:

```bash
python -m src.layer_01_collection.run_layer_01 collect \
  --url "<GOOGLE_MAPS_PLACE_URL>" \
  --sort newest \
  --max-reviews <COUNT> \
  --force-collection
```

The current collector blocks a database that already contains reviews unless `--force-collection` is supplied. A bounded newest-first request can upsert recent records into the existing database; it must be planned deliberately because it is not a scheduler and does not guarantee that the external provider performs a purely incremental fetch.

Important safeguards:

- Never delete an existing database to refresh reviews.
- Confirm `BUSINESS_NAME` and the Google Maps URL before collection.
- Prefer a bounded newest-first refresh when that satisfies the update need.
- Review provider cost and collection scope before using `--force-collection`.
- Do not use collection merely to rebuild analysis or presentations.

The same operation can be routed through the main runner, followed by Layers 02–05:

```bash
python run_all.py --include-collection collect \
  --url "<GOOGLE_MAPS_PLACE_URL>" \
  --sort newest \
  --max-reviews <COUNT> \
  --force-collection
```

Read-only Layer 01 inspection commands are also available:

```bash
python -m src.layer_01_collection.run_layer_01 places
python -m src.layer_01_collection.run_layer_01 stats "<PLACE_ID>"
```

## Scenario C — Only Regenerate Presentations

If data and analysis did not change, do not rerun collection or the analysis pipeline just to change presentation formatting. Edit the relevant source or localization and run only the needed builder.

```bash
# English internal report
.venv/bin/python presentation/build_presentation.py

# German internal report
.venv/bin/python -m presentation.build_presentation_de

# English competitive report
.venv/bin/python competitive_presentation/build_competitive_presentation.py

# German competitive report
.venv/bin/python -m competitive_presentation.build_competitive_presentation_de
```

Builders write to language-specific directories under `output/`. The approved, presentation-oriented copies in [`final_manager_package/`](../final_manager_package/) should only be updated after the newly generated reports pass their QA.

## Individual Analysis Commands

```bash
# Layer 01 — external collection; use only intentionally
python -m src.layer_01_collection.run_layer_01 collect --url "<GOOGLE_MAPS_PLACE_URL>"

# Layer 02 — preparation
python -m src.layer_02_preparation.run_layer_02

# Layer 03 — numerical analysis
python -m src.layer_03_numerical_analysis.run_layer_03

# Layer 04 — text analysis
python -m src.layer_04_text_analysis.run_layer_04

# Layer 05 — reporting
python -m src.layer_05_reporting.run_layer_05
```

Competitive Analysis is separate from the five-layer pipeline:

```bash
python -m src.competitive_analysis.run_competitive_analysis
```

Its supporting ingestion and workbook utilities are documented in [`src/competitive_analysis/README.md`](../src/competitive_analysis/README.md). Do not rerun research ingestion unless its input source actually changed.

## Testing

```bash
.venv/bin/python -m unittest discover -s tests -v
```

The Phase 1 baseline is 82 passing tests.
