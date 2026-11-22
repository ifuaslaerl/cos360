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
            default=Path("Datasets/Satisfactory/scenarios"),
            help="JSON de demanda/estoque ou diretório com cenários Satisfactory",
        )
        parser.add_argument(
            "--output-dir",
            type=Path,
            default=Path("results/satisfactory/scenarios"),
        )
        parser.add_argument(
            "--repeats",
            type=self._minimum_repeats,
            default=10,
            help="repetições por solver (mínimo: 10)",
        )
        options = parser.parse_args(arguments)

        if options.format == "satisfactory" and options.demand_file.is_dir():
            demand_files = sorted(options.demand_file.rglob("scenario_*.json"))
            if not demand_files:
                parser.error(
                    f"nenhum cenário scenario_*.json encontrado em {options.demand_file}"
                )
        else:
            if options.format == "json" and options.demand_file.is_dir():
                parser.error("--demand-file deve ser um arquivo no formato json")
            demand_files = (options.demand_file,)

        total_executions = 0
        if len(demand_files) > 1:
            executions_per_scenario = (
                len(ScipySolverAdapter().available_solvers()) * options.repeats
            )
            print(
                f"[cos360] {len(demand_files)} cenários | "
                f"{executions_per_scenario} execuções por cenário | "
                f"{len(demand_files) * executions_per_scenario} execuções no total"
            )
        for demand_file in demand_files:
            output_dir = options.output_dir
            if len(demand_files) > 1:
                relative_parent = demand_file.parent.relative_to(
                    options.demand_file
                )
                output_dir = output_dir / relative_parent / demand_file.stem
                print(
                    f"\n[cos360] Cenário {demand_file} "
                    f"({options.repeats} repetições por solver)"
                )
            total_executions += self._run_pipeline(options, demand_file, output_dir)
        if len(demand_files) > 1:
            print(f"\n[cos360] Total executado: {total_executions} execução(ões).")
        return 0

    @staticmethod
    def _minimum_repeats(value: str) -> int:
        repeats = int(value)
        if repeats < 10:
            raise argparse.ArgumentTypeError("repeats deve ser no mínimo 10")
        return repeats

    @staticmethod
    def _run_pipeline(
        options: argparse.Namespace,
        demand_file: Path,
        output_dir: Path,
    ) -> int:
        if options.format == "satisfactory":
            from Datasets.Satisfactory.source import SatisfactoryDocsSource
            from Datasets.Satisfactory.standardizer import (
                SatisfactoryDocsStandardizer,
            )

            source = SatisfactoryDocsSource(options.dataset)
            standardizer = SatisfactoryDocsStandardizer(
                demands=DemandConfigSource(demand_file).load(),
                inventories=DemandConfigSource(demand_file).load_inventories(),
            )
        else:
            source = JsonDatasetSource(options.dataset)
            standardizer = DatasetStandardizer()
        pipeline = OptimizationPipeline(
            source,
            standardizer,
            DatasetValidator(),
            OptimizationEngine(),
            ResultWriter(output_dir),
        )
        solutions = pipeline.run(
            (ScipySolverAdapter(),),
            repeats=options.repeats,
            verbose=True,
        )
        return len(solutions)


if __name__ == "__main__":
    raise SystemExit(PipelineRunner().run())
