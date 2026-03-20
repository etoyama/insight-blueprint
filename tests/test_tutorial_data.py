"""Tests for tutorial sample data (sales.csv).

Verify that the shipped CSV has correct schema, coverage, and
statistical patterns needed for the tutorial workflow.
"""

from __future__ import annotations

import csv
import math
from datetime import date
from pathlib import Path

import pytest

TUTORIAL_DIR = Path(__file__).resolve().parent.parent / "tutorial"
SALES_CSV = TUTORIAL_DIR / "sample_data" / "sales.csv"

EXPECTED_COLUMNS = [
    "date",
    "store_id",
    "region",
    "product",
    "price",
    "quantity",
    "revenue",
    "weather",
    "temperature",
    "time_slot",
]

EXPECTED_STORES = {"STORE-A", "STORE-B", "STORE-C"}
EXPECTED_WEATHER = {"sunny", "cloudy", "rainy"}
EXPECTED_TIME_SLOTS = {"morning", "afternoon", "evening"}
EXPECTED_PRODUCTS = {"hot_coffee", "iced_coffee", "latte", "frappuccino"}


def _load_rows() -> list[dict[str, str]]:
    """Load CSV rows as list of dicts."""
    with SALES_CSV.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _pearson_r(xs: list[float], ys: list[float]) -> float:
    """Compute Pearson correlation coefficient."""
    n = len(xs)
    if n < 3:
        return 0.0
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    cov = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys, strict=True))
    std_x = math.sqrt(sum((x - mean_x) ** 2 for x in xs))
    std_y = math.sqrt(sum((y - mean_y) ** 2 for y in ys))
    if std_x * std_y == 0:
        return 0.0
    return cov / (std_x * std_y)


@pytest.fixture(scope="module")
def rows() -> list[dict[str, str]]:
    if not SALES_CSV.exists():
        pytest.skip("tutorial/sample_data/sales.csv not generated yet")
    return _load_rows()


# --- Schema tests ---


def test_csv_has_correct_columns(rows: list[dict[str, str]]) -> None:
    assert list(rows[0].keys()) == EXPECTED_COLUMNS


def test_csv_row_count_in_range(rows: list[dict[str, str]]) -> None:
    assert 400 <= len(rows) <= 600


# --- Coverage tests ---


def test_all_stores_present(rows: list[dict[str, str]]) -> None:
    stores = {r["store_id"] for r in rows}
    assert stores == EXPECTED_STORES


def test_all_weather_types_present(rows: list[dict[str, str]]) -> None:
    weather = {r["weather"] for r in rows}
    assert weather == EXPECTED_WEATHER


def test_all_time_slots_present(rows: list[dict[str, str]]) -> None:
    slots = {r["time_slot"] for r in rows}
    assert slots == EXPECTED_TIME_SLOTS


def test_all_products_present(rows: list[dict[str, str]]) -> None:
    products = {r["product"] for r in rows}
    assert products == EXPECTED_PRODUCTS


def test_date_range_april_to_september(rows: list[dict[str, str]]) -> None:
    dates = [date.fromisoformat(r["date"]) for r in rows]
    assert min(dates) >= date(2025, 4, 1)
    assert max(dates) <= date(2025, 9, 30)


def test_six_months_covered(rows: list[dict[str, str]]) -> None:
    months = {date.fromisoformat(r["date"]).month for r in rows}
    assert months == {4, 5, 6, 7, 8, 9}


# --- Statistical pattern tests ---


def test_afternoon_positive_correlation_temp_vs_iced_revenue(
    rows: list[dict[str, str]],
) -> None:
    """Afternoon: temperature up -> iced coffee revenue up (r > 0.3)."""
    afternoon_iced = [
        r
        for r in rows
        if r["time_slot"] == "afternoon" and r["product"] == "iced_coffee"
    ]
    temps = [float(r["temperature"]) for r in afternoon_iced]
    revenues = [float(r["revenue"]) for r in afternoon_iced]
    r = _pearson_r(temps, revenues)
    assert r > 0.3, f"Expected positive correlation, got r={r:.3f}"


def test_morning_hot_coffee_resilient_to_temperature(
    rows: list[dict[str, str]],
) -> None:
    """Morning: hot coffee revenue does NOT decrease with temperature.

    The reversal pattern: commuter demand keeps hot coffee strong
    even on warm mornings. Correlation should be near zero or positive.
    """
    morning_hot = [
        r for r in rows if r["time_slot"] == "morning" and r["product"] == "hot_coffee"
    ]
    temps = [float(r["temperature"]) for r in morning_hot]
    revenues = [float(r["revenue"]) for r in morning_hot]
    r = _pearson_r(temps, revenues)
    assert r > -0.15, f"Expected near-zero or positive correlation, got r={r:.3f}"


# --- Data integrity tests ---


def test_revenue_equals_price_times_quantity(rows: list[dict[str, str]]) -> None:
    for i, r in enumerate(rows):
        expected = int(r["price"]) * int(r["quantity"])
        actual = int(r["revenue"])
        assert actual == expected, (
            f"Row {i}: {actual} != {int(r['price'])} * {int(r['quantity'])}"
        )


def test_temperature_in_reasonable_range(rows: list[dict[str, str]]) -> None:
    temps = [float(r["temperature"]) for r in rows]
    assert min(temps) >= 5, f"Min temp too low: {min(temps)}"
    assert max(temps) <= 40, f"Max temp too high: {max(temps)}"


def test_quantity_is_positive(rows: list[dict[str, str]]) -> None:
    for i, r in enumerate(rows):
        assert int(r["quantity"]) > 0, f"Row {i}: quantity must be positive"
