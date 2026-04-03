"""Common data preprocessing utilities for batch analysis."""

import pandas as pd


def clean_revenue(df: pd.DataFrame) -> pd.DataFrame:
    """Remove nulls and filter positive revenue values."""
    return df.dropna(subset=["revenue"]).query("revenue > 0")


def one_hot_time_slot(df: pd.DataFrame) -> pd.DataFrame:
    """One-hot encode the time_slot column."""
    return pd.get_dummies(df, columns=["time_slot"], prefix="ts")
