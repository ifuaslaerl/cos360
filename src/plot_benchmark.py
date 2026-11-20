"""Generate time and memory charts from a benchmark CSV."""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path
from statistics import median
from typing import Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "results" / "benchmark.csv"
REQUIRED_COLUMNS = {
    "dataset",
    "items",
    "method",
    "build_seconds",
    "solve_seconds",
    "total_seconds",
    "additional_peak_rss_mib",
}
METHOD_COLORS = {
    "highs": "#1f77b4",
    "highs-ds": "#ff7f0e",
    "highs-ipm": "#2ca02c",
}


def plot_benchmark(
    input_csv: str | Path = DEFAULT_INPUT,
    output_dir: str | Path = ROOT / "results" / "plots",
) -> tuple[Path, Path]:
    """Create runtime and incremental-memory PNG plots and return their paths."""
    input_path = Path(input_csv)
    if not input_path.is_absolute():
        input_path = ROOT / input_path
    with input_path.open(newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        columns = set(reader.fieldnames or ())
        missing = REQUIRED_COLUMNS - columns
        if missing:
            raise ValueError(f"{input_path} is missing columns: {sorted(missing)}")
        rows = list(reader)
    if "status" in (reader.fieldnames or []):
        rows = [row for row in rows if row["status"] == "optimal"]
    if not rows:
        raise ValueError(f"{input_path} contains no successful benchmark rows")

    output_path = Path(output_dir)
    if not output_path.is_absolute():
        output_path = ROOT / output_path
    output_path.mkdir(parents=True, exist_ok=True)

    datasets = sorted({row["dataset"] for row in rows})
    methods = sorted({row["method"] for row in rows})
    runtime_path = output_path / "benchmark_tempo.png"
    memory_path = output_path / "benchmark_memoria.png"
    _plot_metric(
        rows,
        datasets,
        methods,
        ("build_seconds", "solve_seconds", "total_seconds"),
        "Tempo (s)",
        "Tempo por tamanho da instância",
        runtime_path,
    )
    _plot_metric(
        rows,
        datasets,
        methods,
        ("additional_peak_rss_mib",),
        "Memória adicional de pico (MiB)",
        "Memória adicional por tamanho da instância",
        memory_path,
    )
    print(f"CSV: {len(rows)} execuções lidas de {input_path}")
    print(f"Gráficos: {runtime_path} e {memory_path}")
    return runtime_path, memory_path


def _plot_metric(
    rows: Sequence[dict[str, str]],
    datasets: Sequence[str],
    methods: Sequence[str],
    metrics: Sequence[str],
    ylabel: str,
    title: str,
    output_path: Path,
) -> None:
    grouped: dict[tuple[str, str, int, str], list[float]] = defaultdict(list)
    for row in rows:
        for metric in metrics:
            try:
                size = int(row["items"])
                value = float(row[metric])
            except (TypeError, ValueError) as error:
                raise ValueError(f"Invalid numeric value in benchmark row: {row}") from error
            grouped[(row["dataset"], row["method"], size, metric)].append(value)

    figure, axes = plt.subplots(
        1, len(datasets), figsize=(5 * len(datasets), 6.5), squeeze=False
    )
    for axis, dataset in zip(axes[0], datasets):
        for method in methods:
            for metric in metrics:
                points = sorted(
                    (
                        size,
                        median(values),
                    )
                    for (group_dataset, group_method, size, group_metric), values
                    in grouped.items()
                    if group_dataset == dataset
                    and group_method == method
                    and group_metric == metric
                )
                if not points:
                    continue
                label = method if len(metrics) == 1 else f"{method} - {metric.removesuffix('_seconds')}"
                axis.plot(
                    [point[0] for point in points],
                    [point[1] for point in points],
                    marker="o",
                    label=label,
                    color=METHOD_COLORS.get(method),
                    linestyle="-" if metric != "build_seconds" else "--",
                    alpha=0.9 if metric == "total_seconds" or len(metrics) == 1 else 0.6,
                )
        axis.set_title(dataset)
        axis.set_xlabel("Número de itens")
        axis.set_ylabel(ylabel)
        axis.grid(True, alpha=0.3)

    figure.suptitle(title)
    handles, labels = axes[0][0].get_legend_handles_labels()
    if handles:
        figure.legend(
            handles,
            labels,
            loc="lower center",
            ncols=min(6, len(handles)),
            fontsize="small",
        )
    figure.tight_layout(rect=(0, 0.24, 1, 0.94))
    figure.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(figure)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default=str(DEFAULT_INPUT), help="CSV do benchmark")
    parser.add_argument(
        "--output-dir",
        default=str(ROOT / "results" / "plots"),
        help="Pasta de saída dos PNGs",
    )
    args = parser.parse_args()
    plot_benchmark(args.input, args.output_dir)


if __name__ == "__main__":
    main()
