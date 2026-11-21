"""ETL and optimization orchestration."""

from ..domain.solution import Solution
from ..etl.dataset_source import DatasetSource
from ..etl.dataset_standardizer import DatasetStandardizer
from ..etl.dataset_validator import DatasetValidator
from ..etl.result_writer import ResultWriter
from ..optimization.optimization_engine import OptimizationEngine
from ..optimization.solver_adapter import SolverAdapter


class OptimizationPipeline:
    """Runs extraction, standardization, validation, optimization, and loading."""

    def __init__(
        self,
        source: DatasetSource,
        standardizer: DatasetStandardizer,
        validator: DatasetValidator,
        engine: OptimizationEngine,
        writer: ResultWriter,
    ) -> None:
        self.source = source
        self.standardizer = standardizer
        self.validator = validator
        self.engine = engine
        self.writer = writer

    def run(
        self,
        adapters: tuple[SolverAdapter, ...],
        repeats: int = 1,
    ) -> tuple[Solution, ...]:
        instance = self.standardizer.standardize(self.source.load())
        errors = self.validator.validate(instance)
        errors = tuple(self.standardizer.errors) + errors
        if errors:
            return self._write_invalid(instance.dataset, errors)
        solutions: list[Solution] = []
        for adapter in adapters:
            for solver in adapter.available_solvers():
                for repeat in range(1, repeats + 1):
                    solution = self.engine.solve(instance, adapter, solver, repeat)
                    self.writer.write(solution)
                    solutions.append(solution)
        return tuple(solutions)

    def _write_invalid(self, dataset: str, errors: tuple[str, ...]) -> tuple[Solution, ...]:
        solution = Solution(
            dataset,
            "validation",
            0,
            "error",
            None,
            0.0,
            None,
            (),
            errors,
        )
        self.writer.write(solution)
        return (solution,)
