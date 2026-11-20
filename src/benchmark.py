"""Benchmark make-or-buy instances across graph shapes and HiGHS methods."""

from __future__ import annotations

import argparse
import csv
import json
import random
import resource
import subprocess
import sys
from pathlib import Path
from time import perf_counter
from typing import Any, Sequence

from src.engine import MakeOrBuyModel

METHODS = ("highs", "highs-ds", "highs-ipm")
DATASETS = ("chain", "sparse", "dense")
ROOT = Path(__file__).resolve().parents[1]
FIELDS = (
    "dataset",
    "items",
    "arcs",
    "method",
    "repeat",
    "build_seconds",
    "solve_seconds",
    "total_seconds",
    "peak_rss_mib",
    "additional_peak_rss_mib",
    "objective",
)

Costs = Sequence[tuple[float, float]]
Recipes = Sequence[tuple[int, int, float]]

class Benchmark:
    """Run isolated time and memory benchmarks for generated or custom models."""

    def __init__(
        self, output: str | Path = "results/benchmark.csv", seed: int = 2012132752949
    ) -> None:
        self.output = Path(output)
        self.seed = seed

    def run(
        self,
        datasets: Sequence[str] = DATASETS,
        sizes: Sequence[int] = (10, 25, 50),
        methods: Sequence[str] = METHODS,
        repeats: int = 3,
        output: str | Path | None = None,
    ) -> list[dict[str, Any]]:
        """Benchmark synthetic graph datasets and write the results to CSV."""
        self._validate_options(datasets, sizes, methods, repeats)
        if not datasets or not sizes:
            raise ValueError("datasets and sizes must not be empty")
        total = len(datasets) * len(sizes) * len(methods) * repeats
        rows = []
        completed = 0
        for dataset in datasets:
            for size in sizes:
                for method in methods:
                    for repeat in range(1, repeats + 1):
                        completed += 1
                        seed = self.seed + size * 1009 + repeat
                        rows.append(
                            self._run_with_progress(
                                completed,
                                total,
                                dataset,
                                size,
                                method,
                                seed,
                                repeat,
                            )
                        )
        self._validate_objectives(rows)
        self._write_csv(rows, output)
        return rows

    def run_instance(
        self,
        costs: Costs,
        recipes: Recipes,
        methods: Sequence[str] = METHODS,
        repeats: int = 10,
        output: str | Path | None = None,
    ) -> list[dict[str, Any]]:
        """Benchmark a custom instance across methods and isolated processes.

        ``costs`` contains (purchase_cost, production_cost) per item.
        ``recipes`` contains (ingredient_index, product_index, amount).
        Demand is set to one unit for the last item; other items have no demand.
        """
        if not costs:
            raise ValueError("costs must contain at least one item")
        self._validate_options((), (), methods, repeats)
        instance = {
            "costs": list(costs),
            "arcs": list(recipes),
        }
        total = len(methods) * repeats
        rows = []
        completed = 0
        for method in methods:
            for repeat in range(1, repeats + 1):
                completed += 1
                rows.append(
                    self._run_with_progress(
                        completed,
                        total,
                        "custom",
                        len(costs),
                        method,
                        self.seed + repeat,
                        repeat,
                        instance=instance,
                    )
                )
        self._validate_objectives(rows)
        self._write_csv(rows, output)
        return rows

    def _run_with_progress(
        self,
        completed: int,
        total: int,
        dataset: str,
        size: int,
        method: str,
        seed: int,
        repeat: int,
        instance: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        label = f"[{completed}/{total}] {dataset}, n={size}, {method}, rep={repeat}"
        print(f"{label} ...", end="\r", flush=True)
        try:
            row = self._run_isolated(
                dataset, size, method, seed, repeat, instance=instance
            )
        except RuntimeError:
            print(f"{label} falhou", flush=True)
            raise
        print(
            f"{label} {row['total_seconds']:.3f}s, "
            f"RSS {row['peak_rss_mib']:.1f} MiB",
            flush=True,
        )
        return row

    @staticmethod
    def _validate_options(
        datasets: Sequence[str],
        sizes: Sequence[int],
        methods: Sequence[str],
        repeats: int,
    ) -> None:
        if datasets and any(dataset not in DATASETS for dataset in datasets):
            raise ValueError(f"datasets must be selected from {DATASETS}")
        if sizes and any(size < 1 for size in sizes):
            raise ValueError("sizes must be positive integers")
        if not methods or any(not method for method in methods):
            raise ValueError("methods must contain at least one method name")
        if repeats < 1:
            raise ValueError("repeats must be a positive integer")

    @staticmethod
    def _make_instance(
        dataset: str, size: int, seed: int
    ) -> tuple[list[tuple[float, float]], list[tuple[int, int, float]]]:
        rng = random.Random(seed)
        costs = [
            (2.0 + rng.random() * 5.0, 0.25 + rng.random())
            for _ in range(size)
        ]

        if dataset == "chain":
            arcs = [
                (item, item + 1, 0.5 + rng.random())
                for item in range(size - 1)
            ]
        elif dataset == "sparse":
            arcs = []
            for product in range(1, size):
                ingredients = {product - 1}
                if product > 2:
                    ingredients.add(rng.randrange(product - 1))
                arcs.extend(
                    (ingredient, product, 0.5 + rng.random())
                    for ingredient in sorted(ingredients)
                )
        else:
            arcs = [
                (ingredient, product, 0.5 + rng.random())
                for product in range(1, size)
                for ingredient in range(product)
            ]
        return costs, arcs

    @staticmethod
    def _peak_rss_mib() -> float:
        peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        if sys.platform == "darwin":
            return peak / (1024 * 1024)
        return peak / 1024

    @classmethod
    def _measure_instance(
        cls,
        costs: Costs,
        arcs: Recipes,
        method: str,
        dataset: str,
        repeat: int,
    ) -> dict[str, Any]:
        baseline_peak = cls._peak_rss_mib()
        started = perf_counter()
        model = MakeOrBuyModel()
        for index, (purchase_cost, production_cost) in enumerate(costs):
            model.add_item(
                f"item-{index}",
                demand=1.0 if index == len(costs) - 1 else 0.0,
                purchase_cost=purchase_cost,
                production_cost=production_cost,
            )
        for ingredient, product, amount in arcs:
            model.add_recipe(ingredient, product, amount)
        built = perf_counter()

        solution = model.solve(method=method)
        finished = perf_counter()
        peak = cls._peak_rss_mib()
        return {
            "dataset": dataset,
            "items": len(costs),
            "arcs": len(arcs),
            "method": method,
            "repeat": repeat,
            "build_seconds": built - started,
            "solve_seconds": finished - built,
            "total_seconds": finished - started,
            "peak_rss_mib": peak,
            "additional_peak_rss_mib": max(0.0, peak - baseline_peak),
            "objective": solution.total_cost,
        }

    def _run_isolated(
        self,
        dataset: str,
        size: int,
        method: str,
        seed: int,
        repeat: int,
        instance: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        command = [
            sys.executable,
            "-m",
            "src.benchmark",
            "--worker",
            "--dataset",
            dataset,
            "--size",
            str(size),
            "--method",
            method,
            "--seed",
            str(seed),
            "--repeat",
            str(repeat),
        ]
        result = subprocess.run(
            command,
            cwd=ROOT,
            input=json.dumps(instance) if instance is not None else None,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode:
            raise RuntimeError(
                f"Benchmark failed for {dataset}/{size}/{method} "
                f"(repeat {repeat}):\n{result.stderr.strip()}"
            )
        return json.loads(result.stdout)

    @staticmethod
    def _validate_objectives(rows: Sequence[dict[str, Any]]) -> None:
        objectives: dict[tuple[str, int, int], list[float]] = {}
        for row in rows:
            key = (row["dataset"], row["items"], row["repeat"])
            objectives.setdefault(key, []).append(row["objective"])
        for key, values in objectives.items():
            tolerance = 1e-7 * max(1.0, max(map(abs, values)))
            if max(values) - min(values) > tolerance:
                raise RuntimeError(
                    f"Methods returned different objective values for "
                    f"{key}: {values}"
                )

    def _write_csv(
        self, rows: Sequence[dict[str, Any]], output: str | Path | None
    ) -> None:
        destination = Path(output) if output is not None else self.output
        if not destination.is_absolute():
            destination = ROOT / destination
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("w", newline="", encoding="utf-8") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(rows)
        print(f"{len(rows)} execuções gravadas em {destination}")


def _worker(args: argparse.Namespace) -> None:
    if args.dataset == "custom":
        instance = json.load(sys.stdin)
        costs, arcs = instance["costs"], instance["arcs"]
    else:
        costs, arcs = Benchmark._make_instance(
            args.dataset, args.size, args.seed
        )
    row = Benchmark._measure_instance(
        costs, arcs, args.method, args.dataset, args.repeat
    )
    print(json.dumps(row))


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--datasets",
        nargs="+",
        choices=DATASETS,
        default=list(DATASETS),
    )
    parser.add_argument("--sizes", nargs="+", type=int, default=[10, 50, 100, 500, 1000])
    parser.add_argument(
        "--methods", nargs="+", choices=METHODS, default=list(METHODS)
    )
    parser.add_argument("--repeats", type=int, default=10)
    parser.add_argument("--seed", type=int, default=2012132752949)
    parser.add_argument("--output", default="results/benchmark.csv")
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--dataset", help=argparse.SUPPRESS)
    parser.add_argument("--size", type=int, help=argparse.SUPPRESS)
    parser.add_argument("--method", help=argparse.SUPPRESS)
    parser.add_argument("--repeat", type=int, help=argparse.SUPPRESS)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    if args.worker:
        _worker(args)
        return
    Benchmark(output=args.output, seed=args.seed).run(
        datasets=args.datasets,
        sizes=args.sizes,
        methods=args.methods,
        repeats=args.repeats,
    )


if __name__ == "__main__":
    main()
