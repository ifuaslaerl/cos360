"""Simple script entry point for the optimization pipeline."""

import argparse
from pathlib import Path

from ..etl.dataset_standardizer import DatasetStandardizer
from ..etl.dataset_validator import DatasetValidator
from ..etl.json_dataset_source import JsonDatasetSource
from ..etl.result_writer import ResultWriter
from ..optimization.optimization_engine import OptimizationEngine
from ..optimization.scipy_solver_adapter import ScipySolverAdapter
from ..pipeline.optimization_pipeline import OptimizationPipeline


class PipelineRunner:
    """Parses script arguments and executes the configured pipeline."""

    def run(self, arguments: list[str] | None = None) -> int:
        parser = argparse.ArgumentParser()
        parser.add_argument("dataset", type=Path)
        parser.add_argument("--output-dir", default="results/executions")
        parser.add_argument("--repeats", type=int, default=1)
        options = parser.parse_args(arguments)
        pipeline = OptimizationPipeline(
            JsonDatasetSource(options.dataset),
            DatasetStandardizer(),
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
