# Project Map

## If you want to...

| I want to... | Go here |
| --- | --- |
| Find final English manager PDFs | [`final_manager_package/english/`](../final_manager_package/english/) |
| Find final German manager PDFs | [`final_manager_package/deutsch/`](../final_manager_package/deutsch/) |
| Find the original generated package | [`output/final_manager_package/`](../output/final_manager_package/) |
| Run the normal analysis | [`run_all.py`](../run_all.py) |
| Change the active restaurant or core paths | [`config.py`](../config.py) |
| Change review collection | [`src/layer_01_collection/`](../src/layer_01_collection/) |
| Change preparation or cleaning | [`src/layer_02_preparation/`](../src/layer_02_preparation/) |
| Change numerical metrics | [`src/layer_03_numerical_analysis/`](../src/layer_03_numerical_analysis/) |
| Change topic or sentiment analysis | [`src/layer_04_text_analysis/`](../src/layer_04_text_analysis/) |
| Change reporting outputs | [`src/layer_05_reporting/`](../src/layer_05_reporting/) |
| Change competitor comparisons | [`src/competitive_analysis/`](../src/competitive_analysis/) |
| Change the internal presentation | [`presentation/`](../presentation/) |
| Change the competitive presentation | [`competitive_presentation/`](../competitive_presentation/) |
| Change German translations | [`localization/`](../localization/) |
| Find restaurant data | [`businesses/restaurants/`](../businesses/restaurants/) |
| Find the Al Assiel database | [`businesses/restaurants/al_assiel/data/reviews.db`](../businesses/restaurants/al_assiel/data/reviews.db) |
| Find the Olivenzweig database | [`businesses/restaurants/olivenzweig/data/reviews.db`](../businesses/restaurants/olivenzweig/data/reviews.db) |
| Find the Al Safa database | [`businesses/restaurants/al_safa/data/reviews.db`](../businesses/restaurants/al_safa/data/reviews.db) |
| Find the Beit Fayrouz database | [`businesses/restaurants/beit_fayrouz/data/reviews.db`](../businesses/restaurants/beit_fayrouz/data/reviews.db) |
| Find generated analysis | [`output/`](../output/) |
| Find tests | [`tests/`](../tests/) |
| Run tests | [How to Run — Testing](03_HOW_TO_RUN.md#testing) |
| Find technical scripts | [`scripts/`](../scripts/) |
| Find project documentation | [`docs/`](./) |

## Mental Model

### Source Code

Things you edit:

- [`src/`](../src/)
- [`presentation/`](../presentation/)
- [`competitive_presentation/`](../competitive_presentation/)
- [`localization/`](../localization/)
- [`scripts/`](../scripts/)

### Business Data

Things the system reads:

- [`businesses/restaurants/`](../businesses/restaurants/)

Each restaurant contains isolated `inputs/` and `data/reviews.db` locations. Do not move these databases or change their paths casually.

### Generated Outputs

Things the system creates:

- [`output/`](../output/)

### Final Deliverables

Things you present or send:

- [`final_manager_package/`](../final_manager_package/)

For commands, safeguards, and the difference between stored-data analysis and paid collection, see [How to Run](03_HOW_TO_RUN.md).
