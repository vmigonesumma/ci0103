"""Estilo compartido para graficos matplotlib y seaborn.

Uso recomendado en notebooks:

    from plot_style import (
        aplicar_estilo_graficos,
        COLOR_DESTACADO,
        COLORES_MARCAS,
    )
    aplicar_estilo_graficos()

Luego puedes reutilizar `COLORES_MARCAS` al construir cada grafico y
`COLOR_DESTACADO` cuando necesites resaltar un dato puntual.
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


COLORES_SUMMA = {
    "azul_marino": "#031843",
    "verde_agua": "#37968C",
    "celeste": "#00C1D5",
    "petroleo": "#00859B",
    "azul_gris": "#5F92A3",
    "gris": "#656565",
    "burdeos": "#78365F",
}


PALETA_BASE = [
    COLORES_SUMMA["azul_marino"],
    COLORES_SUMMA["verde_agua"],
    COLORES_SUMMA["celeste"],
    COLORES_SUMMA["petroleo"],
    COLORES_SUMMA["azul_gris"],
    COLORES_SUMMA["gris"],
]
# El burdeos se reserva para destacar y no entra al ciclo base.


COLOR_PRINCIPAL = COLORES_SUMMA["azul_marino"]
COLOR_DESTACADO = COLORES_SUMMA["burdeos"]
COLOR_REJILLA = "#D7E1E6"
COLOR_BORDE = "#B8C9D2"


ESTILO_GRAFICOS = {
    "figure.figsize": (12, 6),
    "figure.dpi": 120,
    "savefig.dpi": 200,
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "savefig.facecolor": "white",
    "font.family": "sans-serif",
    "font.sans-serif": [
        "Aptos",
        "Avenir Next",
        "Helvetica Neue",
        "Arial",
        "DejaVu Sans",
    ],
    "font.size": 12,
    "axes.titlesize": 18,
    "axes.titleweight": "bold",
    "axes.labelsize": 13,
    "axes.titlecolor": COLOR_PRINCIPAL,
    "axes.labelcolor": COLOR_PRINCIPAL,
    "text.color": COLOR_PRINCIPAL,
    "axes.edgecolor": COLOR_BORDE,
    "axes.linewidth": 0.8,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "axes.axisbelow": True,
    "grid.color": COLOR_REJILLA,
    "grid.linestyle": "--",
    "grid.linewidth": 0.8,
    "grid.alpha": 0.6,
    "xtick.color": COLOR_PRINCIPAL,
    "ytick.color": COLOR_PRINCIPAL,
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
        Paleta principal. Si no se entrega, usa `PALETA_BASE`
        alineada al brandbook de Summa.
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


def color_marca(marca: str, default: str = COLOR_PRINCIPAL) -> str:
    """Entrega un color fijo por marca y un fallback si no existe."""

    return COLORES_MARCAS.get(marca, default)


def paleta_marcas(
    marcas: list[str] | tuple[str, ...],
    default: str = COLOR_PRINCIPAL,
) -> dict[str, str]:
    """Construye una paleta para pasar directo a seaborn."""

    return {marca: color_marca(marca, default=default) for marca in marcas}
