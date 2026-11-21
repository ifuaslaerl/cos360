"""Simple script entry point for the optimization pipeline."""

import argparse
import sys
from pathlib import Path

if __package__:
    from ..etl.dataset_standardizer import DatasetStandardizer
    from ..etl.dataset_validator import DatasetValidator
    from ..etl.demand_config_source import DemandConfigSource
    from ..etl.json_dataset_source import JsonDatasetSource
    from ..etl.result_writer import ResultWriter
    from ..optimization.optimization_engine import OptimizationEngine
    from ..optimization.scipy_solver_adapter import ScipySolverAdapter
    from ..pipeline.optimization_pipeline import OptimizationPipeline
else:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from src.etl.dataset_standardizer import DatasetStandardizer
    from src.etl.dataset_validator import DatasetValidator
    from src.etl.demand_config_source import DemandConfigSource
    from src.etl.json_dataset_source import JsonDatasetSource
    from src.etl.result_writer import ResultWriter
    from src.optimization.optimization_engine import OptimizationEngine
    from src.optimization.scipy_solver_adapter import ScipySolverAdapter
    from src.pipeline.optimization_pipeline import OptimizationPipeline


class PipelineRunner:
    """Parses script arguments and executes the configured pipeline."""

    def run(self, arguments: list[str] | None = None) -> int:
        parser = argparse.ArgumentParser()
        parser.add_argument(
            "dataset",
            nargs="?",
            type=Path,
            default=Path("Datasets/Satisfactory/Docs.json"),
        )
        parser.add_argument(
            "--format",
            choices=("json", "satisfactory"),
            default="satisfactory",
        )
        parser.add_argument(
            "--demand-file",
            type=Path,
            default=Path("Datasets/Satisfactory/demand.example.json"),
        )
        parser.add_argument("--output-dir", default="results/satisfactory")
        parser.add_argument("--repeats", type=int, default=1)
        options = parser.parse_args(arguments)
        if options.format == "satisfactory":
            from Datasets.Satisfactory.source import SatisfactoryDocsSource
            from Datasets.Satisfactory.standardizer import (
                SatisfactoryDocsStandardizer,
            )

            source = SatisfactoryDocsSource(options.dataset)
            standardizer = SatisfactoryDocsStandardizer(
                demands=DemandConfigSource(options.demand_file).load(),
                inventories=DemandConfigSource(options.demand_file).load_inventories(),
            )
        else:
            source = JsonDatasetSource(options.dataset)
            standardizer = DatasetStandardizer()
        pipeline = OptimizationPipeline(
            source,
            standardizer,
            DatasetValidator(),
            OptimizationEngine(),
            ResultWriter(options.output_dir),
        )
        pipeline.run(
            (ScipySolverAdapter(),),
            repeats=options.repeats,
        )
        return 0


if __name__ == "__main__":
    raise SystemExit(PipelineRunner().run())
