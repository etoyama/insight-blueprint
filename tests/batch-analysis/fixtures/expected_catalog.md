# CATALOG.md

## data_utils.py
- `clean_revenue(df: pd.DataFrame) -> pd.DataFrame`: Remove nulls and filter positive revenue values.
- `one_hot_time_slot(df: pd.DataFrame) -> pd.DataFrame`: One-hot encode the time_slot column.

## viz_utils.py
- `plot_correlation_matrix(df: pd.DataFrame, columns: list[str]) -> None`: Plot a correlation matrix heatmap for specified columns.
