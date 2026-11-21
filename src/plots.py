"""Plots for the make-or-buy model."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import TYPE_CHECKING, Sequence

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
from matplotlib.figure import Figure

if TYPE_CHECKING:
    from src.engine import MakeOrBuyModel, Solution

TOLERANCE = 1e-9
VARIABLES = {"compra": 0, "produção": 1, "estoque": 2}


def plot_graph(
    model: MakeOrBuyModel,
    solution: Solution | None = None,
    output: str | Path | None = None,
    figsize: tuple[float, float] = (10.0, 6.0),
) -> Figure:
    """Draw the recipe graph with the optimal quantities in each node."""
    solution = solution or model.solve()
    graph = nx.DiGraph()
    graph.add_nodes_from(range(len(model.item_names)))
    graph.add_edges_from(model.recipes)
    if nx.is_directed_acyclic_graph(graph):
        layers = dict(enumerate(nx.topological_generations(graph)))
        positions = nx.multipartite_layout(graph, subset_key=layers)
    else:
        positions = nx.circular_layout(graph)

    quantities = {
        "compra": solution.purchases,
        "produção": solution.production,
        "estoque": solution.inventory_used,
    }
    labels, categories = {}, []
    for index, name in enumerate(model.item_names):
        active = {
            kind: values[index]
            for kind, values in quantities.items()
            if values[index] > TOLERANCE
        }
        lines = [name] + [f"{kind}: {value:.1f}" for kind, value in active.items()]
        if model.demands[index]:
            lines.append(f"demanda: {model.demands[index]:g}")
        labels[index] = "\n".join(lines)
        categories.append(" + ".join(active) or "sem atividade")

    colors = plt.get_cmap("tab10")
    palette = {c: colors(i) for i, c in enumerate(sorted(set(categories)))}

    fig = Figure(figsize=figsize)
    ax = fig.subplots()
    nx.draw_networkx_nodes(
        graph, positions, ax=ax, node_size=4500,
        node_color=[palette[c] for c in categories],
    )
    nx.draw_networkx_labels(graph, positions, labels=labels, ax=ax, font_size=8)
    nx.draw_networkx_edges(
        graph, positions, ax=ax, node_size=4500,
        arrowstyle="-|>", connectionstyle="arc3,rad=0.1",
    )
    nx.draw_networkx_edge_labels(
        graph, positions, ax=ax, font_size=8, connectionstyle="arc3,rad=0.1",
        edge_labels={arc: f"{r:.2g}" for arc, r in model.recipes.items()},
    )
    ax.set_title(f"Plano ótimo (custo total {solution.total_cost:.2f})")
    ax.set_axis_off()
    ax.legend(
        handles=[plt.Line2D([], [], marker="o", linestyle="", color=c, label=k)
                 for k, c in palette.items()],
        loc="upper left",
        bbox_to_anchor=(1.0, 1.0),
    )
    return _save(fig, output)


def plot_cost_breakdown(
    model: MakeOrBuyModel,
    solution: Solution | None = None,
    output: str | Path | None = None,
    figsize: tuple[float, float] = (10.0, 5.0),
) -> Figure:
    """Stacked bars with the purchase and production cost of each item."""
    solution = solution or model.solve()
    purchase = solution.purchases * model.purchase_costs
    production = solution.production * model.production_costs
    positions = np.arange(len(model.item_names))

    fig = Figure(figsize=figsize)
    ax = fig.subplots()
    ax.bar(positions, purchase, label="Compra")
    ax.bar(positions, production, bottom=purchase, label="Produção")
    ax.set_xticks(positions, model.item_names, rotation=45, ha="right")
    ax.set_title(f"Custo ótimo por item (total {solution.total_cost:.2f})")
    ax.set_xlabel("Item")
    ax.set_ylabel("Custo")
    ax.legend()
    return _save(fig, output)


def plot_demand_sensitivity(
    model: MakeOrBuyModel,
    item: str | int,
    demands: Sequence[float],
    output: str | Path | None = None,
    figsize: tuple[float, float] = (8.0, 5.0),
) -> Figure:
    """Optimal cost as a function of one item's demand (convex, piecewise linear)."""
    demands = sorted(demands)
    variant = deepcopy(model)
    costs = []
    for demand in demands:
        variant.set_demand(item, demand)
        costs.append(variant.solve().total_cost)
    name = item if isinstance(item, str) else model.item_names[item]

    fig = Figure(figsize=figsize)
    ax = fig.subplots()
    ax.plot(demands, costs, marker="o", label="Custo ótimo")
    ax.set_title(f"Custo ótimo em função da demanda de {name}")
    ax.set_xlabel("Demanda")
    ax.set_ylabel("Custo ótimo")
    ax.legend()
    return _save(fig, output)


def plot_feasible_region(
    model: MakeOrBuyModel,
    x_variable: tuple[str, str],
    y_variable: tuple[str, str],
    solution: Solution | None = None,
    limits: tuple[float, float] | None = None,
    resolution: int = 400,
    output: str | Path | None = None,
    figsize: tuple[float, float] = (8.0, 6.0),
) -> Figure:
    """Plot a 2D slice of the feasible region with cost level curves and the optimum."""
    solution = solution or model.solve()
    lp = model.export_linear_program()
    optimum = np.column_stack(
        [solution.purchases, solution.production, solution.inventory_used]
    ).ravel()
    i = _variable_index(model, x_variable)
    j = _variable_index(model, y_variable)

    high = limits[1] if limits else 2 * max(optimum[i], optimum[j], 1.0)
    low = limits[0] if limits else 0.0
    xs = np.linspace(low, high, resolution)
    ys = np.linspace(low, high, resolution)
    X, Y = np.meshgrid(xs, ys)

    rest = lp.limits - lp.inequalities @ optimum
    rest = rest + lp.inequalities[:, i] * optimum[i] + lp.inequalities[:, j] * optimum[j]
    lhs = lp.inequalities[:, [i]][:, :, None] * X + lp.inequalities[:, [j]][:, :, None] * Y
    slack = rest[:, None, None] - lhs
    feasible = (slack >= -TOLERANCE).all(axis=0)
    for var, grid in ((i, X), (j, Y)):
        upper = lp.bounds[var][1]
        feasible &= grid >= lp.bounds[var][0] - TOLERANCE
        if upper is not None:
            feasible &= grid <= upper + TOLERANCE

    cost = lp.objective[i] * X + lp.objective[j] * Y
    fig = Figure(figsize=figsize)
    ax = fig.subplots()
    ax.contourf(X, Y, feasible, levels=[0.5, 1.5], colors=["#9ecae1"], alpha=0.6)
    levels = ax.contour(
        X, Y, np.where(feasible, cost, np.nan), levels=10, cmap="Oranges"
    )
    ax.clabel(levels, fmt="%.0f", fontsize=8)
    for row in np.flatnonzero(lp.inequalities[:, [i, j]].any(axis=1)):
        if (slack[row] < 0).any() and (slack[row] > 0).any():
            ax.contour(X, Y, slack[row], levels=[0], colors="k", linewidths=1)
    ax.plot(optimum[i], optimum[j], "r*", markersize=16, label="Ótimo")
    ax.set_xlim(low, high)
    ax.set_ylim(low, high)
    ax.set_xlabel(_variable_label(x_variable))
    ax.set_ylabel(_variable_label(y_variable))
    ax.set_title("Região viável (azul), curvas de nível do custo e ótimo")
    ax.legend()
    return _save(fig, output)


def _variable_index(model: MakeOrBuyModel, variable: tuple[str, str]) -> int:
    kind, item = variable
    return 3 * model.item_index[item] + VARIABLES[kind]


def _variable_label(variable: tuple[str, str]) -> str:
    return f"{variable[0]} de {variable[1]}"


def _save(fig: Figure, output: str | Path | None) -> Figure:
    if output is not None:
        path = Path(output)
        path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(path, dpi=150, bbox_inches="tight")
    return fig
