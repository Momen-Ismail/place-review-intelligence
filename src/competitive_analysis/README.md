# Competitive analysis

This package compares the four independent Layer 05 restaurant analyses; it is
not a sixth layer and it does not invoke review collection.

Run it with:

```bash
.venv/bin/python scripts/ingest_competitor_research_pdf.py
.venv/bin/python -m src.competitive_analysis.run_competitive_analysis
.venv/bin/python scripts/build_competitive_workbook.py
```

The configurable formal cutoff is stored in
`businesses/restaurants/competitive_config.json`. For the initial benchmark it
is 2026-09-03. UTC calendar-date windows are identical for every restaurant:

- latest 30 days: 2026-08-05 through 2026-09-03
- previous 30 days: 2026-07-06 through 2026-08-04
- recent 90 days: 2026-06-06 through 2026-09-03
- previous 90 days: 2026-03-08 through 2026-06-05
- historical: through 2026-03-07

Evidence levels use the existing project thresholds: none for zero supporting
reviews, low for 1–4, medium for 5–14, and high for 15 or more. Observed leaders
also need the configured minimum sample size; ties produce no unique leader.
Platform popularity is retained as a separate menu/platform signal and is never
added to Google review sentiment or presented as sales volume.

Original menu categories are preserved in `original_category_counts`. The
separate `normalized_comparison_groups` map restaurant-specific labels into
non-exclusive business groups; those group counts must not be summed. Missing
source coverage is reported as `unknown`, not as zero availability. Breakfast
and brunch are independent signals.

The supplied competitive-intelligence PDF is a supporting snapshot dated
2026-09-20. It sits below current official, owned-menu, Google, and current
platform sources. Conflicting prices are retained with source/date/conflict
metadata rather than silently overwritten.
