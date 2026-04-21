"""Estilo compartido para graficos matplotlib y seaborn.

Uso recomendado en notebooks:

    from plot_style import aplicar_estilo_graficos, COLORES_MARCAS
    aplicar_estilo_graficos()

Luego puedes reutilizar `COLORES_MARCAS` al construir cada grafico.
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import seaborn as sns


COLORES_MARCAS = {
    "SAN JORGE": "#2E8B57",
    "LA PREFERIDA": "#D62728",
    "WINTER": "#F1C40F",
    "Los Nogales": "#7D3C98",
}


PALETA_BASE = [
    "#2E8B57",
    "#D62728",
    "#F1C40F",
    "#7D3C98",
    "#4C78A8",
    "#F58518",
    "#72B7B2",
    "#E45756",
]


ESTILO_GRAFICOS = {
    "figure.figsize": (12, 6),
    "figure.dpi": 120,
    "savefig.dpi": 200,
    "font.family": "Arial",
    "font.size": 12,
    "axes.titlesize": 18,
    "axes.titleweight": "bold",
    "axes.labelsize": 13,
    "axes.edgecolor": "#B0B0B0",
    "axes.linewidth": 0.8,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.color": "#D9D9D9",
    "grid.linestyle": "--",
    "grid.linewidth": 0.8,
    "grid.alpha": 0.45,
    "xtick.labelsize": 11,
    "ytick.labelsize": 11,
    "legend.fontsize": 11,
    "legend.frameon": False,
    "lines.linewidth": 2,
}


def aplicar_estilo_graficos(
    *,
    estilo_seaborn: str = "whitegrid",
    palette: list[str] | None = None,
    reset: bool = True,
) -> dict:
    """Aplica un estilo consistente para matplotlib y seaborn.

    Parameters
    ----------
    estilo_seaborn:
        Estilo base de seaborn. Por defecto usa "whitegrid".
    palette:
        Paleta principal. Si no se entrega, usa `PALETA_BASE`.
    reset:
        Si es True, restablece `rcParams` antes de aplicar el estilo.
    """

    if reset:
        plt.rcParams.update(plt.rcParamsDefault)

    rc = ESTILO_GRAFICOS.copy()
    colores = palette or PALETA_BASE
    rc["axes.prop_cycle"] = plt.cycler(color=colores)

    sns.set_theme(style=estilo_seaborn, rc=rc)
    sns.set_palette(colores)
    return rc


def color_marca(marca: str, default: str = "#4C78A8") -> str:
    """Entrega un color fijo por marca y un fallback si no existe."""

    return COLORES_MARCAS.get(marca, default)


def paleta_marcas(
    marcas: list[str] | tuple[str, ...],
    default: str = "#4C78A8",
) -> dict[str, str]:
    """Construye una paleta para pasar directo a seaborn."""

    return {marca: color_marca(marca, default=default) for marca in marcas}
