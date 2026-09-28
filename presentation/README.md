# Management presentation

Build the Al Assiel management presentation from the current Layer 05 and Layer
04 analysis outputs:

```bash
python3 presentation/build_presentation.py
```

The builder validates the required analysis sections, profile facts, menu counts,
and stable review totals. It opens SQLite in read-only/query-only mode for review
metadata and exact source text, then deterministically selects anonymous quote
excerpts. Every excerpt is validated against its Layer 04 evidence clause and
original or translated review text before compilation.

It then generates `presentation_data.tex`, `presentation_appendix.tex`, chart
CSVs, and a quote manifest; compiles the 16:9 Beamer source with
latexmk/LuaLaTeX in a temporary directory; and renders every slide to PNG for
visual inspection. The current deck has 39 management/roadmap pages and a
61-page evidence/action appendix (100 pages total). Its 16 chapters have separate dividers. The
appendix contains complete latest-30-day, previous-30-day, and low-score case
registers, all observed dish/item evidence, operational negative-case pages,
action checklists, and KPI definitions. Public original-review URLs are included
without loading or exposing reviewer identity fields. The builder validates
internal destinations and external-link syntax before compilation. The final PDF
is written to:

```text
output/restaurants/al_assiel/presentation/
al_assiel_review_intelligence_presentation.pdf
```

Layer 05 is the numeric source of truth; Layer 04 supplies topic, sentiment, and
dish evidence; the restaurant profile supplies operational facts such as buffet
days and hours. Presentation source files live under `presentation/`; generated
data, the PDF, quote manifest, chart inputs, and rendered slides live under
`output/`.
