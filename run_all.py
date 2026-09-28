"""Run the complete local analysis pipeline, with optional paid collection."""

import argparse


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run Layers 02–05. Collection runs only when explicitly requested."
    )
    parser.add_argument(
        "--include-collection",
        action="store_true",
        help="Run Layer 01 first and forward remaining collection arguments.",
    )
    args, collection_args = parser.parse_known_args()

    if args.include_collection:
        from src.layer_01_collection.run_layer_01 import main as run_collection

        if not collection_args or collection_args[0] not in {"collect", "places", "stats"}:
            collection_args.insert(0, "collect")
        run_collection(collection_args)
    elif collection_args:
        parser.error("collection arguments require --include-collection")

    from src.layer_02_preparation.run_layer_02 import run as run_layer_02
    from src.layer_03_numerical_analysis.run_layer_03 import run as run_layer_03
    from src.layer_04_text_analysis.run_layer_04 import run as run_layer_04
    from src.layer_05_reporting.run_layer_05 import run as run_layer_05

    run_layer_02()
    run_layer_03()
    run_layer_04()
    run_layer_05()


if __name__ == "__main__":
    main()
