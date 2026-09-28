# Place Review Intelligence

Place Review Intelligence collects Google Maps reviews through Apify, stores the
source data in SQLite, and runs a five-layer restaurant analysis. The active
business and every input/output path are controlled in `config.py`.

## Project structure

```text
place-review-intelligence/
├── config.py
├── run_all.py
├── requirements.txt
├── businesses/restaurants/al_assiel/
│   ├── inputs/
│   │   ├── restaurant_profile.json
│   │   ├── menu_catalog.json
│   │   └── management_observations.json
│   └── data/
│       └── reviews.db
├── src/
│   ├── common/
│   │   ├── data_loader.py
│   │   ├── evidence.py
│   │   ├── json_utils.py
│   │   └── text_utils.py
│   ├── layer_01_collection/
│   │   ├── step_01_fetch_google_reviews.py
│   │   ├── step_02_normalize_reviews.py
│   │   ├── step_03_store_reviews.py
│   │   ├── step_04_export_reviews.py
│   │   └── run_layer_01.py
│   ├── layer_02_preparation/
│   ├── layer_03_numerical_analysis/
│   ├── layer_04_text_analysis/
│   └── layer_05_reporting/
└── output/restaurants/al_assiel/
    ├── layer_01_collection/
    ├── layer_02_preparation/
    ├── layer_03_numerical_analysis/
    ├── layer_04_text_analysis/
    └── layer_05_reporting/
```

Each layer directory contains numbered `step_*.py` files and its own
`run_layer_*.py` entry point. Generated files always go under `output/`, never
under `src/`.

## Data flow

```text
Google
  ↓
Layer 01 Collection
  ↓
reviews.db
  ↓
Layer 02 Preparation
  ↓
layer_02_prepared_reviews.json
  ├──→ Layer 03 Numerical Analysis
  │      ↓
  │    layer_03_numerical_analysis.json
  └──→ Layer 04 Text Analysis
         ↓
       layer_04_text_analysis.json

Layer 03 + Layer 04
  ↓
Layer 05 Reporting
  ↓
final JSON + Excel workbook
```

## Layers and commands

Activate the project environment first:

```bash
source .venv/bin/activate
```

Layer 01 fetches, normalizes, stores, deduplicates, and optionally exports
reviews. Running it without arguments safely lists the existing places and does
not contact Apify:

```bash
python -m src.layer_01_collection.run_layer_01
python -m src.layer_01_collection.run_layer_01 places
python -m src.layer_01_collection.run_layer_01 stats PLACE_ID
```

Collection is explicit because it can consume Apify credits:

```bash
python -m src.layer_01_collection.run_layer_01 collect \
  --url 'GOOGLE_MAPS_URL' \
  --max-reviews 100 \
  --sort newest \
  --language en \
  --personal-data \
  --export-csv \
  --export-excel
```

Omit `--max-reviews` to collect all available reviews. Use
`--no-personal-data` to disable reviewer profile data.

Run analysis layers independently:

```bash
python -m src.layer_02_preparation.run_layer_02
python -m src.layer_03_numerical_analysis.run_layer_03
python -m src.layer_04_text_analysis.run_layer_04
python -m src.layer_05_reporting.run_layer_05
```

Run the complete local analysis:

```bash
python run_all.py
```

The default master runner starts at Layer 02 and never contacts Apify. To
collect first, pass the existing Layer 01 options explicitly:

```bash
python run_all.py --include-collection --url 'GOOGLE_MAPS_URL' --export-excel
```

## Inputs, data, and outputs

- Human-maintained profile:
  `businesses/restaurants/al_assiel/inputs/restaurant_profile.json`
- Human-maintained menu:
  `businesses/restaurants/al_assiel/inputs/menu_catalog.json`
- Human-maintained management observations and proposed experiments:
  `businesses/restaurants/al_assiel/inputs/management_observations.json`
- Persistent collected data:
  `businesses/restaurants/al_assiel/data/reviews.db`
- Generated artifacts:
  `output/restaurants/al_assiel/`

Layer 02 validates the database schema and both JSON inputs, selects one text
variant per semantic review, normalizes it, and creates an inspectable prepared
JSON file. It does not make business conclusions.

Layer 03 calculates overall distributions, Google structured ratings, review
context, engagement, languages, monthly trends, and recent/historical
comparisons. It also owns review-cadence and owner-response analytics. Missing
structured ratings remain missing; they are never treated as zero.

Review cadence uses the newest valid review timestamp as the reproducible anchor
for recent and previous 30/90-day windows. Average, median, shortest, and longest
days between reviews come from the actual consecutive timestamps inside each
period; they are not approximated as `period days / review count`. Reviews per
week and per 30 days use the calendar duration of the corresponding period.

Owner-response analytics report overall, rating-level, low-score, and period
response rates. A response exists when response text or an owner-response date
is present. Delay statistics are calculated only when both valid timestamps are
available and the response does not predate the review. Diagnostic follow-up
rows contain review IDs and timestamps but no reviewer personal information.

Layer 04 analyzes written review topics and menu dishes. Sentiment uses explicit
positive/negative alias polarity first, then sentiment terms in the same local
clause. Simple negation and contrast clauses are handled. Overall star rating is
never a topic or dish sentiment fallback. Original and translated copies of the
same review are not added together.

Longest menu matches win. Generic Kibbeh, Shawarma, and Falafel expressions are
kept as ambiguous dish-family evidence rather than assigned to an arbitrary menu
item; a specific phrase such as `shawarma sandwich` still maps exactly. Google
recommended dishes absent from the menu are reported as unmapped and are not
silently added to the catalog.

Evidence levels are shared across the analysis: zero reviews is none, 1–4 is
low, 5–14 is medium, and 15+ is high. Strength and weakness evidence is based on
the supporting positive or negative review count, respectively. Topic and dish
rating rankings require five review mentions; dish best/worst comparisons also
require at least three qualified dishes. Rankings never use zero-value filler.

Layer 04 also provides buffet-local analysis, low/high rating associations,
recent-90-day emerging issues, a documented priority heuristic, a compact data
quality report, and review-level topic/dish match evidence. The emerging method
requires at least two recent review mentions and a five-percentage-point increase;
signals supported by 2–4 recent reviews are explicitly labelled low-evidence
possible emerging issues/strengths. It is a transparent signal rather than a
causal claim. Topics with qualifying positive and negative changes are shown as
mixed/polarizing rather than duplicated as simple management conclusions.

Improvement priorities require at least two negative reviews. The deterministic
score is `(negative reviews + negative share % / 5 + negative coverage % of
written reviews + (positive recent-negative change / 4 × recent-signal evidence
weight)) × negative-evidence weight`, where
the evidence level is based on negative-review count. Total topic mentions do not
independently raise the score.
Recent deterioration is additionally multiplied by the emerging complaint's
own evidence weight. Monthly overall and structured trends mark incomplete first
and last dataset months as partial. Translation quality uses non-English written
reviews as its denominator because English reviews need no English translation.

The topic period-comparison engine applies the same calculation to configured
service, food, value, menu, drinks, environment, access, and buffet topics. It
reports historical, previous-90-day, and recent-90-day counts, written-review
coverage, sentiment shares, and rating context. Percentage-point changes are
`null` whenever either comparison rate has no valid denominator.

Low-rating diagnostics keep one-star, two-star, and combined one/two-star groups
separate. They include negative, positive, and neutral topic evidence, recent vs
historical complaint coverage, topic co-occurrence, dish/family mentions, owner
response status, and an anonymous review-ID evidence set. Presentation-facing
co-occurrences require at least two supporting reviews; raw evidenced pairs are
retained for audit.

Buffet subtopics are matched only inside clauses that contain buffet evidence.
This prevents nearby à-la-carte wording from being assigned to buffet quality,
freshness, variety, replenishment, value, or queue experience. Each buffet
subtopic carries its own evidence level and period comparison.

Menu analysis measures observable review attention across the maintained menu
catalog. It reports items and categories with exact dish evidence, plus customer
favourite signals labelled “most discussed” and “most positively discussed.”
Review attention is not sales or order volume. The required zero-attention label
is “no observable review mentions.”

Layer 05 combines Layers 03 and 04 and creates a business-facing JSON and Excel
workbook. It exposes cadence, owner responses, topic periods, low-score analysis,
buffet diagnostics, menu review attention, customer favourite signals, the
customer journey, a kitchen-versus-bar review-attention view, a dedicated
bar/drinks analysis, menu-management insights, and a management baseline for a
later four-week plan. Complaint evidence is labelled from the number of negative
reviews supporting the issue, separately from total topic evidence. The
Profile and Menu Catalog remain reference sheets in Excel. Google structured
Food/Service/Atmosphere ratings remain separate from sentiment inferred from
written mentions of those topics.

The management baseline contains current ratings, negative shares, review flow,
owner-response rates, recent issue counts, menu and drink attention, and recent buffet
evidence. It intentionally contains no improvement target. Lifetime Google
rating changes slowly, so future action-plan monitoring can emphasize recent
30/90-day measures and low-score response handling.

## Evidence-source separation

The final outputs preserve three distinct sources:

- **Review-derived data**: deterministic calculations from prepared Google
  reviews, topic/dish evidence, ratings, timestamps, and owner responses.
- **Internal management observations**: human-maintained statements in
  `management_observations.json`; these are never presented as review-proven.
- **Proposed actions or experiments**: ideas to test and measure, not established
  benefits or causal conclusions.

The customer-journey section repeats this source label on every evidence,
observation, and action entry. For example, parking availability is a maintained
profile fact, limited parking feedback is customer evidence, and the belief that
parking is not promoted clearly enough is an internal observation. The analysis
does not claim to prove current Google-profile visibility.

Use `layer_04_text_analysis.json` for detailed debugging and match evidence. Use
the Layer 05 JSON/Excel outputs for management reporting.

## Debugging

- Collection, normalization, SQLite, or raw export issue: Layer 01
- Database loading, schema, profile, menu, or prepared text issue: Layer 02
- Rating, context, engagement, or trend issue: Layer 03
- Topic, sentiment, dish, or ranking issue: Layer 04
- Combined JSON or Excel issue: Layer 05

Each runner prints its inputs, review count, output path, completion status, and
execution time. Run only the failing layer while debugging.

## Adding another restaurant

1. Create `businesses/restaurants/NEW_NAME/inputs/` and `data/`.
2. Add `restaurant_profile.json`, `menu_catalog.json`, and `reviews.db`.
3. Change `BUSINESS_NAME` in `config.py`.
4. Run Layer 02 through Layer 05, or `python run_all.py`.

The output path changes automatically from the central configuration.
