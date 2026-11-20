"""Summarize benchmark results and generate plots and written observations."""

from __future__ import annotations

import argparse
import csv
from collections import Counter, defaultdict
from pathlib import Path
from statistics import median
from typing import Any, Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "results" / "benchmark.csv"
DEFAULT_OUTPUT = ROOT / "results" / "analysis"
NUMERIC_FIELDS = (
    "items",
    "repeat",
    "build_seconds",
    "solver_model_seconds",
    "solve_seconds",
    "total_seconds",
    "peak_rss_mib",
    "additional_peak_rss_mib",
)


def analyze_benchmark(
    input_csv: str | Path = DEFAULT_INPUT,
    output_dir: str | Path = DEFAULT_OUTPUT,
) -> dict[str, Path]:
    """Analyze the benchmark CSV, writing summaries, plots, and observations."""
    input_path = Path(input_csv)
    if not input_path.is_absolute():
        input_path = ROOT / input_path
    with input_path.open(newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        rows = list(reader)
        fields = set(reader.fieldnames or ())
    required = {
        "dataset",
        "items",
        "method",
        "backend",
        "solver",
        "status",
        "error",
        "objective",
        *NUMERIC_FIELDS,
    }
    missing = required - fields
    if missing:
        raise ValueError(f"{input_path} is missing columns: {sorted(missing)}")
    if not rows:
        raise ValueError(f"{input_path} contains no benchmark rows")
    for row in rows:
        for field in NUMERIC_FIELDS:
            row[field] = float(row[field])
        row["items"] = int(row["items"])
        row["repeat"] = int(row["repeat"])
        row["objective"] = (
            float(row["objective"]) if row["objective"] else None
        )

    output_path = Path(output_dir)
    if not output_path.is_absolute():
        output_path = ROOT / output_path
    output_path.mkdir(parents=True, exist_ok=True)

    successful = [row for row in rows if row["status"] == "optimal"]
    failed = [row for row in rows if row["status"] != "optimal"]
    solver_summary = _solver_summary(rows)
    size_summary = _size_summary(rows)
    method_size_summary = _method_size_summary(successful)
    failure_summary = _failure_summary(failed)
    _write_csv(
        output_path / "solver_summary.csv",
        solver_summary,
        (
            "method",
            "backend",
            "solver",
            "runs",
            "successes",
            "failures",
            "success_rate_pct",
            "median_total_seconds",
            "p90_total_seconds",
            "median_solve_seconds",
            "median_peak_rss_mib",
        ),
    )
    _write_csv(
        output_path / "dataset_size_summary.csv",
        size_summary,
        (
            "dataset",
            "items",
            "runs",
            "successes",
            "success_rate_pct",
            "median_total_seconds",
            "median_peak_rss_mib",
        ),
    )
    _write_csv(
        output_path / "failure_summary.csv",
        failure_summary,
        ("method", "dataset", "items", "error_type", "count"),
    )
    _write_csv(
        output_path / "method_size_summary.csv",
        method_size_summary,
        (
            "method",
            "items",
            "runs",
            "min_total_seconds",
            "median_total_seconds",
            "max_total_seconds",
            "min_peak_rss_mib",
            "median_peak_rss_mib",
            "max_peak_rss_mib",
        ),
    )

    runtime_plot = output_path / "tempo_total.png"
    memory_plot = output_path / "memoria_rss.png"
    success_plot = output_path / "taxa_sucesso.png"
    _plot_range_by_solver_size(
        successful, "total_seconds", "Tempo total (s)", runtime_plot
    )
    _plot_range_by_solver_size(
        successful, "peak_rss_mib", "Pico RSS total do processo (MiB)", memory_plot
    )
    _plot_success_rate(rows, success_plot)

    observations_path = output_path / "observacoes.md"
    observations_path.write_text(
        _make_observations(rows, successful, failed, solver_summary, size_summary),
        encoding="utf-8",
    )
    outputs = {
        "observations": observations_path,
        "solver_summary": output_path / "solver_summary.csv",
        "dataset_size_summary": output_path / "dataset_size_summary.csv",
        "method_size_summary": output_path / "method_size_summary.csv",
        "failure_summary": output_path / "failure_summary.csv",
        "runtime_plot": runtime_plot,
        "memory_plot": memory_plot,
        "success_plot": success_plot,
    }
    print(
        f"Análise: {len(rows)} execuções, {len(successful)} ótimas, "
        f"{len(failed)} falhas"
    )
    for name, path in outputs.items():
        print(f"{name}: {path}")
    return outputs


def _solver_summary(rows: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row["method"]].append(row)
    summary = []
    for method, group in sorted(grouped.items()):
        successful = [row for row in group if row["status"] == "optimal"]
        summary.append(
            {
                "method": method,
                "backend": group[0]["backend"],
                "solver": group[0]["solver"],
                "runs": len(group),
                "successes": len(successful),
                "failures": len(group) - len(successful),
                "success_rate_pct": 100 * len(successful) / len(group),
                "median_total_seconds": _median(successful, "total_seconds"),
                "p90_total_seconds": _percentile(successful, "total_seconds", 0.9),
                "median_solve_seconds": _median(successful, "solve_seconds"),
                "median_peak_rss_mib": _median(successful, "peak_rss_mib"),
            }
        )
    return summary


def _size_summary(rows: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(row["dataset"], row["items"])].append(row)
    summary = []
    for (dataset, items), group in sorted(grouped.items()):
        successful = [row for row in group if row["status"] == "optimal"]
        summary.append(
            {
                "dataset": dataset,
                "items": items,
                "runs": len(group),
                "successes": len(successful),
                "success_rate_pct": 100 * len(successful) / len(group),
                "median_total_seconds": _median(successful, "total_seconds"),
                "median_peak_rss_mib": _median(successful, "peak_rss_mib"),
            }
        )
    return summary


def _failure_summary(rows: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    counts = Counter(
        (
            row["method"],
            row["dataset"],
            int(row["items"]),
            _error_type(row["error"]),
        )
        for row in rows
    )
    return [
        {
            "method": method,
            "dataset": dataset,
            "items": items,
            "error_type": error_type,
            "count": count,
        }
        for (method, dataset, items, error_type), count in sorted(counts.items())
    ]


def _method_size_summary(
    rows: Sequence[dict[str, Any]],
) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(row["method"], int(row["items"]))].append(row)
    summary = []
    for (method, items), group in sorted(grouped.items()):
        total_times = [float(row["total_seconds"]) for row in group]
        peak_memory = [float(row["peak_rss_mib"]) for row in group]
        summary.append(
            {
                "method": method,
                "items": items,
                "runs": len(group),
                "min_total_seconds": min(total_times),
                "median_total_seconds": median(total_times),
                "max_total_seconds": max(total_times),
                "min_peak_rss_mib": min(peak_memory),
                "median_peak_rss_mib": median(peak_memory),
                "max_peak_rss_mib": max(peak_memory),
            }
        )
    return summary


def _plot_range_by_solver_size(
    rows: Sequence[dict[str, Any]],
    metric: str,
    ylabel: str,
    output_path: Path,
) -> None:
    methods = sorted({row["method"] for row in rows})
    sizes = sorted({int(row["items"]) for row in rows})
    grouped: dict[tuple[str, int], list[float]] = defaultdict(list)
    for row in rows:
        grouped[(row["method"], int(row["items"]))].append(
            float(row[metric])
        )

    figure, axis = plt.subplots(figsize=(max(14, len(methods) * 1.15), 8))
    method_positions = np.arange(len(methods), dtype=float)
    size_offsets = np.linspace(-0.32, 0.32, len(sizes))
    size_colors = plt.get_cmap("viridis")(
        np.linspace(0.12, 0.88, max(len(sizes), 2))
    )
    for size_index, size in enumerate(sizes):
        x_values = []
        medians = []
        lower_errors = []
        upper_errors = []
        for method_index, method in enumerate(methods):
            values = grouped.get((method, size))
            if not values:
                continue
            lower = min(values)
            center = median(values)
            upper = max(values)
            x_values.append(method_positions[method_index] + size_offsets[size_index])
            medians.append(center)
            lower_errors.append(center - lower)
            upper_errors.append(upper - center)
        axis.errorbar(
            x_values,
            medians,
            yerr=(lower_errors, upper_errors),
            fmt="o",
            markersize=5,
            capsize=3,
            elinewidth=1.1,
            color=size_colors[size_index],
            label=f"{size} itens",
        )
    axis.set_xticks(method_positions, labels=methods, rotation=35, ha="right")
    axis.set_ylabel(ylabel)
    axis.set_yscale("log")
    axis.set_title(
        f"{ylabel}: mínimo, mediana e máximo por solver e tamanho\n"
        "Intervalo calculado sobre datasets e repetições bem-sucedidas"
    )
    axis.grid(True, which="both", axis="y", alpha=0.25)
    axis.legend(title="Tamanho", ncols=min(5, len(sizes)), frameon=False)
    figure.tight_layout()
    figure.savefig(output_path, dpi=160, bbox_inches="tight")
    plt.close(figure)


def _plot_success_rate(rows: Sequence[dict[str, Any]], output_path: Path) -> None:
    methods = sorted({row["method"] for row in rows})
    sizes = sorted({int(row["items"]) for row in rows})
    datasets = sorted({row["dataset"] for row in rows})
    matrix = np.zeros((len(methods), len(sizes)), dtype=float)
    for method_index, method in enumerate(methods):
        for size_index, size in enumerate(sizes):
            selected = [
                row
                for row in rows
                if row["method"] == method and int(row["items"]) == size
            ]
            matrix[method_index, size_index] = (
                100
                * sum(row["status"] == "optimal" for row in selected)
                / len(selected)
            )

    figure, axis = plt.subplots(figsize=(9, max(5, len(methods) * 0.42)))
    image = axis.imshow(matrix, aspect="auto", vmin=0, vmax=100, cmap="RdYlGn")
    axis.set_xticks(range(len(sizes)), labels=sizes)
    axis.set_yticks(range(len(methods)), labels=methods)
    axis.set_xlabel("Número de itens")
    axis.set_title(f"Taxa de sucesso por solver (agregada em {len(datasets)} datasets)")
    for row_index in range(len(methods)):
        for col_index in range(len(sizes)):
            axis.text(
                col_index,
                row_index,
                f"{matrix[row_index, col_index]:.0f}%",
                ha="center",
                va="center",
                fontsize=8,
            )
    figure.colorbar(image, ax=axis, label="Execuções ótimas (%)")
    figure.tight_layout()
    figure.savefig(output_path, dpi=160, bbox_inches="tight")
    plt.close(figure)


def _make_observations(
    rows: Sequence[dict[str, Any]],
    successful: Sequence[dict[str, Any]],
    failed: Sequence[dict[str, Any]],
    solver_summary: Sequence[dict[str, Any]],
    size_summary: Sequence[dict[str, Any]],
) -> str:
    datasets = sorted({row["dataset"] for row in rows})
    sizes = sorted({int(row["items"]) for row in rows})
    methods = sorted({row["method"] for row in rows})
    expected = len(datasets) * len(sizes) * len(methods) * len(
        {int(row["repeat"]) for row in rows}
    )
    failure_counts = Counter(row["method"] for row in failed)
    error_counts = Counter(_error_type(row["error"]) for row in failed)
    worst_solver = max(solver_summary, key=lambda row: row["failures"])
    size_rows = sorted(size_summary, key=lambda row: (row["items"], row["dataset"]))
    largest_rows = [row for row in size_summary if row["items"] == max(sizes)]
    densest = next(row for row in largest_rows if row["dataset"] == "dense")
    chain = next(row for row in largest_rows if row["dataset"] == "chain")
    fastest_large = min(
        (
            row
            for row in solver_summary
            if row["successes"] and row["method"].startswith("scipy/highs")
        ),
        key=lambda row: row["median_total_seconds"],
    )
    rss_worst = max(successful, key=lambda row: row["peak_rss_mib"])

    spreads: dict[tuple[str, int, int], list[float]] = defaultdict(list)
    for row in successful:
        if row["objective"] is not None:
            spreads[(row["dataset"], int(row["items"]), int(row["repeat"]))].append(
                float(row["objective"])
            )
    max_spread = max(
        (max(values) - min(values) for values in spreads.values() if len(values) > 1),
        default=0.0,
    )

    lines = [
        "# Análise do benchmark",
        "",
        f"Arquivo analisado: `{DEFAULT_INPUT.name}`.",
        "",
        "## Resumo",
        "",
        f"- Execuções observadas: **{len(rows)}**; matriz esperada: **{expected}**.",
        f"- Soluções ótimas: **{len(successful)} ({100 * len(successful) / len(rows):.2f}%)**.",
        f"- Falhas de execução: **{len(failed)} ({100 * len(failed) / len(rows):.2f}%)**.",
        f"- Solvers comparados: **{len(methods)}**; datasets: **{', '.join(datasets)}**.",
        "",
        "## Observações",
        "",
        f"1. **Falhas concentradas:** `{worst_solver['method']}` teve "
        f"{worst_solver['failures']}/{worst_solver['runs']} falhas "
        f"({100 - worst_solver['success_rate_pct']:.1f}%); "
        f"tipos registrados: {', '.join(f'{name} ({count})' for name, count in error_counts.most_common())}.",
        f"2. **Escala:** em {max(sizes)} itens, o tempo total mediano agregado "
        f"foi {chain['median_total_seconds']:.2f}s para cadeia e "
        f"{densest['median_total_seconds']:.2f}s para dense; o RSS mediano foi "
        f"{chain['median_peak_rss_mib']:.1f} MiB e {densest['median_peak_rss_mib']:.1f} MiB, respectivamente.",
        f"3. **HiGHS:** `{fastest_large['method']}` foi o método HiGHS mais rápido "
        f"pela mediana geral ({fastest_large['median_total_seconds']:.4f}s), "
        "mas médias/medianas gerais são fortemente influenciadas pelos tamanhos grandes.",
        f"4. **Memória de pico:** o maior valor foi {rss_worst['peak_rss_mib']:.1f} MiB "
        f"em {rss_worst['dataset']}, n={int(rss_worst['items'])}, "
        f"`{rss_worst['method']}`. RSS inclui Python, bibliotecas e solver.",
        f"5. **Concordância numérica:** maior diferença entre objetivos ótimos "
        f"para instâncias/repetições correspondentes: {max_spread:.3g}.",
        "6. `additional_peak_rss_mib` é incremento sobre o pico já atingido antes "
        "da chamada ao solver; por isso muitos valores são zero. Para comparar "
        "processos, use `peak_rss_mib` e lembre que cada biblioteca tem overhead "
        "de importação diferente.",
        "7. Os gráficos consolidados mostram, em cada solver e tamanho, a mediana "
        "e a faixa mínimo–máximo sobre datasets e repetições; o eixo de tempo e "
        "RSS está em escala logarítmica.",
        "",
        "## Resumo por solver",
        "",
        "| Solver | Sucesso | Mediana total (s) | P90 total (s) | Mediana RSS (MiB) |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in sorted(solver_summary, key=lambda item: item["median_total_seconds"]):
        lines.append(
            f"| `{row['method']}` | {row['successes']}/{row['runs']} "
            f"({row['success_rate_pct']:.1f}%) | {row['median_total_seconds']:.4f} "
            f"| {row['p90_total_seconds']:.4f} | {row['median_peak_rss_mib']:.1f} |"
        )
    lines.extend(
        [
            "",
            "## Resumo por dataset e tamanho",
            "",
            "| Dataset | Itens | Sucesso | Mediana total (s) | Mediana RSS (MiB) |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    for row in size_rows:
        lines.append(
            f"| {row['dataset']} | {row['items']} | {row['successes']}/{row['runs']} "
            f"({row['success_rate_pct']:.1f}%) | {row['median_total_seconds']:.4f} "
            f"| {row['median_peak_rss_mib']:.1f} |"
        )
    if failed:
        lines.extend(["", "## Falhas por solver", ""])
        for method, count in failure_counts.most_common():
            lines.append(f"- `{method}`: {count}")
    lines.append("")
    return "\n".join(lines)


def _median(rows: Sequence[dict[str, Any]], field: str) -> float:
    return median(float(row[field]) for row in rows) if rows else float("nan")


def _percentile(
    rows: Sequence[dict[str, Any]], field: str, quantile: float
) -> float:
    values = sorted(float(row[field]) for row in rows)
    if not values:
        return float("nan")
    return values[round((len(values) - 1) * quantile)]


def _error_type(message: str) -> str:
    if "Iteration limit reached" in message:
        return "Iteration limit reached"
    if "Phase 1" in message:
        return "Simplex Phase 1 numerical failure"
    if "feasible" in message and "optimal" in message:
        return "Feasible but not reported optimal"
    return message.split(":", maxsplit=1)[0] or "Unknown error"


def _write_csv(
    path: Path, rows: Sequence[dict[str, Any]], fieldnames: Sequence[str]
) -> None:
    with path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default=str(DEFAULT_INPUT), help="Benchmark CSV")
    parser.add_argument(
        "--output-dir", default=str(DEFAULT_OUTPUT), help="Analysis output folder"
    )
    args = parser.parse_args()
    analyze_benchmark(args.input, args.output_dir)


if __name__ == "__main__":
    main()
