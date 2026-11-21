"""Command-line script for generating Satisfactory test scenarios."""

import argparse
import sys
from pathlib import Path

if __package__:
    from ..etl.scenario_generator import SatisfactoryScenarioGenerator
else:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from src.etl.scenario_generator import SatisfactoryScenarioGenerator

from Datasets.Satisfactory.source import SatisfactoryDocsSource
from Datasets.Satisfactory.standardizer import SatisfactoryDocsStandardizer


class ScenarioGeneratorRunner:
    """Loads Docs.json and generates random demand/inventory files."""

    def run(self, arguments: list[str] | None = None) -> int:
        parser = argparse.ArgumentParser()
        parser.add_argument(
            "--docs-file",
            type=Path,
            default=Path("Datasets/Satisfactory/Docs.json"),
        )
        parser.add_argument(
            "--output-dir",
            type=Path,
            default=Path("Datasets/Satisfactory/scenarios"),
        )
        parser.add_argument("--orders", nargs="+", type=int, default=(10, 100, 1000))
        parser.add_argument("--cases-per-order", type=int, default=5)
        parser.add_argument("--items-per-scenario", type=int, default=5)
        parser.add_argument("--seed", type=int, default=360)
        options = parser.parse_args(arguments)

        payload = SatisfactoryDocsSource(options.docs_file).load()
        instance = SatisfactoryDocsStandardizer().standardize(payload)
        for order in options.orders:
            if order < 1:
                raise ValueError("orders must be positive")
            output_dir = options.output_dir / f"order_{order}"
            generator = SatisfactoryScenarioGenerator(
                output_dir,
                [item.id for item in instance.items],
                seed=options.seed + order,
            )
            paths = generator.generate(
                count=options.cases_per_order,
                items_per_scenario=options.items_per_scenario,
                demand_range=(order, order * 10 - 1),
                inventory_range=(order, order * 10 - 1),
            )
            for path in paths:
                print(path)
        return 0


if __name__ == "__main__":
    raise SystemExit(ScenarioGeneratorRunner().run())
