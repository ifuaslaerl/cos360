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
        verbose: bool = False,
    ) -> tuple[Solution, ...]:
        if verbose:
            print("[cos360] Carregando e padronizando o dataset...")
        instance = self.standardizer.standardize(self.source.load())
        if verbose:
            print(
                f"[cos360] Dataset: {instance.dataset} | "
                f"Itens: {len(instance.items)} | Receitas: {len(instance.recipes)}"
            )
        errors = self.validator.validate(instance)
        errors = tuple(self.standardizer.errors) + errors
        if errors:
            if verbose:
                print(f"[cos360] Falha na validação: {len(errors)} erro(s).")
                for error in errors:
                    print(f"[cos360]   - {error}")
            return self._write_invalid(instance.dataset, errors)
        if verbose:
            print("[cos360] Validação concluída com sucesso.")
        solutions: list[Solution] = []
        for adapter in adapters:
            solvers = adapter.available_solvers()
            for solver in solvers:
                for repeat in range(1, repeats + 1):
                    if verbose:
                        print(
                            f"[cos360] Executando {adapter.name}/{solver} "
                            f"(repetição {repeat}/{repeats})..."
                        )
                    solution = self.engine.solve(instance, adapter, solver, repeat)
                    result_path, error_path = self.writer.write(solution)
                    solutions.append(solution)
                    if verbose:
                        print(
                            f"[cos360]   Status: {solution.status} | "
                            f"Objetivo: {solution.objective} | "
                            f"Tempo: {solution.elapsed_seconds:.3f}s"
                        )
                        print(f"[cos360]   Resultado: {result_path}")
                        if error_path is not None:
                            print(f"[cos360]   Erros: {error_path}")
        if verbose:
            print(f"[cos360] Concluído: {len(solutions)} execução(ões).")
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
