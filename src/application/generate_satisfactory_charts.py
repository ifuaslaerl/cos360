"""Command-line script for charting Satisfactory optimization results."""

import argparse
import re
import sys
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

if __package__:
    pass
else:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

matplotlib.use("Agg")

ORDER_PATTERN = re.compile(r"order_(\d+)")
SCENARIO_PATTERN = re.compile(r"(scenario_\d+)")


class ChartGeneratorRunner:
    """Loads execution CSVs and renders aggregate and per-scenario charts."""

    def run(self, arguments: list[str] | None = None) -> int:
        parser = argparse.ArgumentParser()
        parser.add_argument(
            "--results-dir",
            type=Path,
            default=Path("results/satisfactory/scenarios"),
        )
        parser.add_argument(
            "--output-dir",
            type=Path,
            default=Path("results/satisfactory/graficos"),
        )
        parser.add_argument("--top-items", type=int, default=15)
        options = parser.parse_args(arguments)

        executions, items = self._load(options.results_dir)
        if executions.empty:
            parser.error(f"nenhum CSV de resultado encontrado em {options.results_dir}")
        options.output_dir.mkdir(parents=True, exist_ok=True)

        sns.set_theme(style="whitegrid")
        self._tempo_por_solver(executions, options.output_dir)
        self._memoria_por_solver(executions, options.output_dir)
        self._objetivo_por_ordem(executions, options.output_dir)
        self._custo_por_item_top(items, options.output_dir, options.top_items)
        self._compra_vs_producao(items, options.output_dir, options.top_items)
        print(f"[cos360] Gráficos gerados em {options.output_dir}")
        return 0

    @staticmethod
    def _load(results_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
        execution_rows = []
        item_rows = []
        for path in sorted(results_dir.rglob("*.csv")):
            if path.name.endswith("__errors.csv"):
                continue
            frame = pd.read_csv(path)
            if frame.empty:
                continue
            order_match = ORDER_PATTERN.search(str(path))
            scenario_match = SCENARIO_PATTERN.search(str(path))
            frame["Ordem"] = int(order_match.group(1)) if order_match else 0
            frame["Cenario"] = scenario_match.group(1) if scenario_match else path.stem
            execution_rows.append(
                frame[
                    [
                        "Solver",
                        "Status",
                        "Objetivo",
                        "Tempo",
                        "Memória",
                        "Repetição",
                        "Ordem",
                        "Cenario",
                    ]
                ].iloc[[0]]
            )
            if frame.loc[0, "Status"] == "optimal":
                item_rows.append(frame)
        executions = (
            pd.concat(execution_rows, ignore_index=True)
            if execution_rows
            else pd.DataFrame()
        )
        items = pd.concat(item_rows, ignore_index=True) if item_rows else pd.DataFrame()
        return executions, items

    @staticmethod
    def _tempo_por_solver(executions: pd.DataFrame, output_dir: Path) -> None:
        optimal = executions[executions["Status"] == "optimal"]
        figure, axis = plt.subplots(figsize=(10, 6))
        sns.boxplot(data=optimal, x="Solver", y="Tempo", ax=axis)
        axis.set_ylabel("Tempo (s)")
        axis.set_title("Tempo de execução por solver")
        axis.tick_params(axis="x", rotation=30)
        figure.tight_layout()
        figure.savefig(output_dir / "tempo_por_solver.png", dpi=150)
        plt.close(figure)

    @staticmethod
    def _memoria_por_solver(executions: pd.DataFrame, output_dir: Path) -> None:
        optimal = executions[executions["Status"] == "optimal"]
        figure, axis = plt.subplots(figsize=(10, 6))
        sns.boxplot(data=optimal, x="Solver", y="Memória", ax=axis)
        axis.set_ylabel("Memória de pico (MiB)")
        axis.set_title("Memória de pico por solver")
        axis.tick_params(axis="x", rotation=30)
        figure.tight_layout()
        figure.savefig(output_dir / "memoria_por_solver.png", dpi=150)
        plt.close(figure)

    @staticmethod
    def _objetivo_por_ordem(executions: pd.DataFrame, output_dir: Path) -> None:
        optimal = executions[executions["Status"] == "optimal"]
        figure, axis = plt.subplots(figsize=(10, 6))
        sns.boxplot(data=optimal, x="Ordem", y="Objetivo", ax=axis)
        axis.set_yscale("log")
        axis.set_ylabel("Custo total (escala log)")
        axis.set_title("Custo total ótimo por ordem de grandeza do cenário")
        figure.tight_layout()
        figure.savefig(output_dir / "objetivo_por_ordem.png", dpi=150)
        plt.close(figure)

    @staticmethod
    def _largest_scenario_rows(items: pd.DataFrame) -> pd.DataFrame:
        largest_order = items["Ordem"].max()
        candidates = items[
            (items["Ordem"] == largest_order) & (items["Solver"] == "scipy/highs")
        ]
        if candidates.empty:
            candidates = items[items["Ordem"] == largest_order]
        first_scenario = candidates["Cenario"].iloc[0]
        rows = candidates[candidates["Cenario"] == first_scenario]
        return rows[rows["Repetição"] == rows["Repetição"].iloc[0]]

    def _custo_por_item_top(
        self, items: pd.DataFrame, output_dir: Path, top_items: int
    ) -> None:
        if items.empty:
            return
        rows = self._largest_scenario_rows(items)
        top = rows.sort_values("Custo", ascending=False).head(top_items)
        figure, axis = plt.subplots(figsize=(10, 6))
        sns.barplot(data=top, y="Item", x="Custo", ax=axis, orient="h")
        axis.set_xlabel("Custo (pontos AWESOME equivalentes)")
        axis.set_title(f"Top {top_items} itens por custo total")
        figure.tight_layout()
        figure.savefig(output_dir / "custo_por_item_top.png", dpi=150)
        plt.close(figure)

    def _compra_vs_producao(
        self, items: pd.DataFrame, output_dir: Path, top_items: int
    ) -> None:
        if items.empty:
            return
        rows = self._largest_scenario_rows(items)
        rows = rows.copy()
        rows["Total"] = rows["Compra"] + rows["Produção"]
        top = rows.sort_values("Total", ascending=False).head(top_items)
        melted = top.melt(
            id_vars="Item",
            value_vars=["Compra", "Produção"],
            var_name="Origem",
            value_name="Quantidade",
        )
        figure, axis = plt.subplots(figsize=(10, 6))
        sns.barplot(data=melted, y="Item", x="Quantidade", hue="Origem", ax=axis)
        axis.set_title(f"Compra vs. Produção (top {top_items} itens)")
        figure.tight_layout()
        figure.savefig(output_dir / "compra_vs_producao.png", dpi=150)
        plt.close(figure)


if __name__ == "__main__":
    raise SystemExit(ChartGeneratorRunner().run())
