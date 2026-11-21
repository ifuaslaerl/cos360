"""CSV persistence for optimization executions."""

import csv
from pathlib import Path

from ..domain.solution import Solution


class ResultWriter:
    """Writes one result CSV and one error report per execution."""

    def __init__(self, output_dir: str | Path = "results/executions") -> None:
        self.output_dir = Path(output_dir)

    def write(self, solution: Solution) -> tuple[Path, Path | None]:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        stem = self._safe_name(
            f"{solution.dataset}__{solution.solver}__rep{solution.repeat}"
        )
        result_path = self.output_dir / f"{stem}.csv"
        fields = (
            "Dataset",
            "Solver",
            "Tempo",
            "Memória",
            "Repetição",
            "Status",
            "Objetivo",
            "Item",
            "Compra",
            "Produção",
            "EstoqueUtilizado",
            "Custo",
        )
        with result_path.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=fields)
            writer.writeheader()
            for row in solution.rows or ({},):
                writer.writerow(
                    {
                        "Dataset": solution.dataset,
                        "Solver": solution.solver,
                        "Tempo": solution.elapsed_seconds,
                        "Memória": solution.peak_memory_mib,
                        "Repetição": solution.repeat,
                        "Status": solution.status,
                        "Objetivo": solution.objective,
                        **row,
                    }
                )
        error_path = None
        if solution.errors:
            error_path = self.output_dir / f"{stem}__errors.csv"
            with error_path.open("w", newline="", encoding="utf-8") as file:
                writer = csv.DictWriter(file, fieldnames=("Dataset", "Solver", "Erro"))
                writer.writeheader()
                writer.writerows(
                    {
                        "Dataset": solution.dataset,
                        "Solver": solution.solver,
                        "Erro": error,
                    }
                    for error in solution.errors
                )
        return result_path, error_path

    @staticmethod
    def _safe_name(value: str) -> str:
        return "".join(character if character.isalnum() or character in "-_." else "_" for character in value)
