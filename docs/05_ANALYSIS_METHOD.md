# Analysis Method

## The Five Layers

### Layer 01 — Collection

Optionally acquires Google Maps reviews through the configured external collector, normalizes the source payload, upserts review and place records into the selected SQLite database, and can export readable collection files. It is intentionally excluded from the normal stored-data run.

### Layer 02 — Preparation

Loads the selected restaurant database, validates the restaurant profile and menu catalog, and prepares one normalized analytical text for each semantic review.

### Layer 03 — Numerical Analysis

Calculates overall and structured ratings, language and review context, monthly and period trends, review cadence, and owner-response metrics.

### Layer 04 — Text Analysis

Performs topic-local sentiment analysis, topic and dish evidence extraction, low-score diagnostics, buffet and menu attention analysis, emerging signals, rankings, and business-priority calculations.

### Layer 05 — Reporting

Combines the prepared, numerical, and text results with management observations, then exports business-facing JSON and Excel reports.

## Competitive Analysis

Competitive Analysis compares the four isolated restaurant analyses using one formal cutoff and identical calendar windows. It is **not** called Layer 06.

Formal cutoff: **03 Sep 2026**

| Period | Inclusive dates |
| --- | --- |
| Latest 30 | 05 Aug – 03 Sep 2026 |
| Previous 30 | 06 Jul – 04 Aug 2026 |
| Recent 90 | 06 Jun – 03 Sep 2026 |
| Previous 90 | 08 Mar – 05 Jun 2026 |
| Historical | Through 07 Mar 2026 |

These periods are configured in [`businesses/restaurants/competitive_config.json`](../businesses/restaurants/competitive_config.json). Reviews after the cutoff remain in their source database but are excluded from formal comparison metrics.

## Evidence Thresholds

Evidence labels are deterministic and based on supporting reviews:

| Supporting reviews | Evidence level |
| ---: | --- |
| 0 | none |
| 1–4 | low |
| 5–14 | medium |
| 15+ | high |

Additional leader and comparative thresholds are defined in the competitive configuration.

## Analytical Guardrails

- **Review attention is not sales.** Mentions show what reviewers discuss, not quantity sold, revenue, or margin.
- **Topic sentiment is local.** Sentiment belongs to the relevant topic or clause; whole-review stars are not used as a topic-sentiment fallback.
- **Unknown is not false.** An unobserved service or capability remains unknown unless a source establishes its absence.
- **Missing evidence is not zero.** Lack of evidence is reported as unavailable or none, not converted into a measured zero.
- **Menu mappings are analytical normalization.** Normalized groups may differ from printed menu sections, and overlapping groups must not be summed as independent inventory.
- **Observed competitor evidence does not prove universal superiority.** The comparison reports documented signals within the defined sources and windows.

For implementation details, use the [Project Map](02_PROJECT_MAP.md). For the supported commands, use [How to Run](03_HOW_TO_RUN.md).
