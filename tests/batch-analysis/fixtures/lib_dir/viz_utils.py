"""Visualization utility functions."""

import matplotlib.pyplot as plt
import pandas as pd


def plot_correlation_matrix(df: pd.DataFrame, columns: list[str]) -> None:
    """Plot a correlation matrix heatmap for specified columns."""
    _corr = df[columns].corr()
    _fig, _ax = plt.subplots(figsize=(8, 6))
    _im = _ax.imshow(_corr, cmap="coolwarm", vmin=-1, vmax=1)
    _ax.set_xticks(range(len(columns)))
    _ax.set_xticklabels(columns, rotation=45)
    _ax.set_yticks(range(len(columns)))
    _ax.set_yticklabels(columns)
    plt.colorbar(_im)
    plt.tight_layout()
