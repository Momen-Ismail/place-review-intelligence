# Data and Databases

## Isolation Model

Each restaurant has an isolated directory with its own business inputs and persistent SQLite review database. The selected `BUSINESS_NAME` in [`config.py`](../config.py) determines which directory the five-layer analysis reads.

Databases preserve collected review history and should not normally be deleted. Reusing them avoids unnecessary recollection, retains provenance, and allows later before/after analysis.

## Database Paths and Current Counts

| Restaurant | Database | Stored reviews |
| --- | --- | ---: |
| Al Assiel | [`businesses/restaurants/al_assiel/data/reviews.db`](../businesses/restaurants/al_assiel/data/reviews.db) | 298 |
| Olivenzweig | [`businesses/restaurants/olivenzweig/data/reviews.db`](../businesses/restaurants/olivenzweig/data/reviews.db) | 718 |
| Al Safa | [`businesses/restaurants/al_safa/data/reviews.db`](../businesses/restaurants/al_safa/data/reviews.db) | 2,696 |
| Beit Fayrouz | [`businesses/restaurants/beit_fayrouz/data/reviews.db`](../businesses/restaurants/beit_fayrouz/data/reviews.db) | 82 |

Al Assiel's validated snapshot contains:

- 298 total reviews
- 220 written reviews
- Google rating: 4.5
- collected average rating: approximately 4.483221

## Business Inputs

Each restaurant's `inputs/` directory contains the structured profile, menu catalog, management observations, and source register used by the analysis:

- [`businesses/restaurants/al_assiel/inputs/`](../businesses/restaurants/al_assiel/inputs/)
- [`businesses/restaurants/olivenzweig/inputs/`](../businesses/restaurants/olivenzweig/inputs/)
- [`businesses/restaurants/al_safa/inputs/`](../businesses/restaurants/al_safa/inputs/)
- [`businesses/restaurants/beit_fayrouz/inputs/`](../businesses/restaurants/beit_fayrouz/inputs/)

The formal restaurant set, comparison cutoff, shared periods, and minimum evidence thresholds are in [`businesses/restaurants/competitive_config.json`](../businesses/restaurants/competitive_config.json).

## Inputs, Database, Analysis Output, and Final Presentation

| Category | Purpose | Location |
| --- | --- | --- |
| Inputs | Curated restaurant profile, menu, management observations, and source register | `businesses/restaurants/<restaurant>/inputs/` |
| Database | Persistent collected review records and place metadata | `businesses/restaurants/<restaurant>/data/reviews.db` |
| Analysis output | Generated layer JSON, Excel, audits, and working presentation files | [`output/`](../output/) |
| Final presentation | Approved PDFs for management use | [`final_manager_package/`](../final_manager_package/) |

Changing an input can change analysis. Changing a database changes the evidence base. Generated output can be recreated from the relevant source data and code, but approved final presentations should only be replaced after QA.

## Credentials and Privacy

`.env` contains external-service credentials and must remain local. It is ignored by Git. `.env.example` contains placeholders only. Do not copy credentials into documentation, configuration files, tests, or reports.

Review databases and exports may contain source metadata or reviewer information. Keep the repository private when appropriate and minimize personal information in externally shared artifacts.
