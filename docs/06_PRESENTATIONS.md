# Presentations

## Final Management PDFs

### English

- [`final_manager_package/english/01_Al_Assiel_Management_Review.pdf`](../final_manager_package/english/01_Al_Assiel_Management_Review.pdf) — internal management report, 106 pages.
- [`final_manager_package/english/02_Al_Assiel_Competitive_Intelligence.pdf`](../final_manager_package/english/02_Al_Assiel_Competitive_Intelligence.pdf) — competitive report, 67 pages.

### German

- [`final_manager_package/deutsch/01_Al_Assiel_Managementbericht.pdf`](../final_manager_package/deutsch/01_Al_Assiel_Managementbericht.pdf) — German internal management report, 106 pages.
- [`final_manager_package/deutsch/02_Al_Assiel_Wettbewerbsanalyse.pdf`](../final_manager_package/deutsch/02_Al_Assiel_Wettbewerbsanalyse.pdf) — German competitive report, 67 pages.

The English and German reports use the same analytical values. German versions localize the validated presentation content; they are not separate analyses.

## Generated Source Package

The unchanged generated source copies remain in [`output/final_manager_package/`](../output/final_manager_package/):

- `01_Al_Assiel_Management_Review.pdf`
- `02_Al_Assiel_Competitive_Intelligence.pdf`
- `03_Al_Assiel_Management_Review_DE.pdf`
- `04_Al_Assiel_Competitive_Intelligence_DE.pdf`

The root [`final_manager_package/`](../final_manager_package/) is the clean presentation-oriented package. Its four PDFs are byte-identical copies of these approved files, with manager-friendly German filenames.

## Builders and Localization

| Responsibility | Source location |
| --- | --- |
| English internal report | [`presentation/`](../presentation/) |
| German internal report | [`presentation/build_presentation_de.py`](../presentation/build_presentation_de.py) |
| English competitive report | [`competitive_presentation/`](../competitive_presentation/) |
| German competitive report | [`competitive_presentation/build_competitive_presentation_de.py`](../competitive_presentation/build_competitive_presentation_de.py) |
| Shared German terminology and translations | [`localization/`](../localization/) |

## Build Commands

Run from the repository root:

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

Do not manually edit generated PDFs. Edit the relevant source, generator, or localization resource; rebuild only the affected report; run its QA; and promote the result only after validation. If analysis did not change, do not rerun collection or the analytical layers solely for presentation formatting.

See [How to Run](03_HOW_TO_RUN.md) for pipeline commands and safeguards.
