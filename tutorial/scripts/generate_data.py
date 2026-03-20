#!/usr/bin/env python3
"""Generate synthetic coffee chain sales data for the tutorial.

Usage:
    python tutorial/scripts/generate_data.py

Output:
    tutorial/sample_data/sales.csv (~500 rows, seed=42)

Embedded patterns:
    - Afternoon: temperature up -> iced coffee revenue up (positive correlation)
    - Morning: hot coffee stays strong regardless of temperature (commuter demand)
    - This "morning reversal" is the aha-moment users discover in the tutorial.
"""

from __future__ import annotations

import csv
import random
from datetime import date, timedelta
from pathlib import Path

SEED = 42
OUTPUT_PATH = Path(__file__).resolve().parent.parent / "sample_data" / "sales.csv"

STORES = [
    ("STORE-A", "downtown"),
    ("STORE-B", "suburban"),
    ("STORE-C", "coastal"),
]

PRODUCTS = {
    "hot_coffee": 350,
    "iced_coffee": 400,
    "latte": 450,
    "frappuccino": 500,
}

WEATHER_TYPES = ["sunny", "cloudy", "rainy"]
TIME_SLOTS = ["morning", "afternoon", "evening"]

# Monthly base temperature ranges (min, max) in Celsius
MONTH_TEMP = {
    4: (12, 22),
    5: (16, 26),
    6: (20, 28),
    7: (25, 34),
    8: (26, 35),
    9: (21, 30),
}

# Monthly rain probability
MONTH_RAIN_PROB = {
    4: 0.25,
    5: 0.20,
    6: 0.45,  # rainy season
    7: 0.15,
    8: 0.15,
    9: 0.25,
}

START_DATE = date(2025, 4, 1)
END_DATE = date(2025, 9, 30)


def _generate_weather(rng: random.Random, month: int) -> str:
    rain_prob = MONTH_RAIN_PROB[month]
    r = rng.random()
    if r < rain_prob:
        return "rainy"
    if r < rain_prob + 0.4:
        return "cloudy"
    return "sunny"


def _generate_temperature(
    rng: random.Random, month: int, weather: str, store_id: str
) -> float:
    lo, hi = MONTH_TEMP[month]
    base = rng.uniform(lo, hi)
    # Weather adjustment
    if weather == "sunny":
        base += rng.uniform(0, 3)
    elif weather == "rainy":
        base -= rng.uniform(0, 3)
    # Coastal stores are slightly warmer in summer
    if store_id == "STORE-C" and month in (7, 8):
        base += 2
    return round(base, 1)


def _compute_quantity(
    rng: random.Random,
    product: str,
    temperature: float,
    weather: str,
    time_slot: str,
    store_id: str,
) -> int:
    # Base quantities
    base = {"hot_coffee": 18, "iced_coffee": 14, "latte": 10, "frappuccino": 7}[product]

    temp_delta = temperature - 22  # deviation from "neutral" temperature

    if time_slot == "morning":
        # KEY PATTERN: Morning commuter demand keeps hot coffee strong
        if product == "hot_coffee":
            base += 8  # commuter bonus (dominant factor)
            base += rng.randint(-2, 2)  # small noise, temperature barely matters
        elif product == "iced_coffee":
            # Weak temperature effect in morning
            base += int(temp_delta * 0.08)
            base += rng.randint(-2, 2)
        else:
            base += rng.randint(-1, 2)

    elif time_slot == "afternoon":
        # KEY PATTERN: Clear temperature -> iced correlation
        if product == "iced_coffee":
            base += int(temp_delta * 0.6)  # strong positive effect
            base += rng.randint(-1, 2)
        elif product == "hot_coffee":
            base -= int(temp_delta * 0.3)  # negative effect
            base += rng.randint(-1, 1)
        elif product == "frappuccino":
            base += int(temp_delta * 0.4)
            base += rng.randint(-1, 2)
        else:
            base += rng.randint(-1, 2)

    else:  # evening
        if product == "iced_coffee":
            base += int(temp_delta * 0.3)
        elif product == "hot_coffee":
            base -= int(temp_delta * 0.15)
        base += rng.randint(-2, 2)

    # Weather effects
    if weather == "rainy":
        if product == "hot_coffee":
            base += 3
        else:
            base = int(base * 0.85)
    elif weather == "sunny" and product in ("iced_coffee", "frappuccino"):
        base += 2

    # Store effects
    if store_id == "STORE-C" and product == "frappuccino":
        base += 3  # coastal store sells more frappuccinos

    return max(1, base)


def generate_sales_data(seed: int = SEED) -> list[dict[str, str | int | float]]:
    """Generate synthetic sales data with embedded patterns."""
    rng = random.Random(seed)
    rows: list[dict[str, str | int | float]] = []

    current = START_DATE
    while current <= END_DATE:
        # Sample ~28% of days to get ~500 total rows
        if rng.random() > 0.28:
            current += timedelta(days=1)
            continue

        for store_id, region in STORES:
            weather = _generate_weather(rng, current.month)
            temperature = _generate_temperature(rng, current.month, weather, store_id)

            # Each store has 1-2 time slots per day
            day_slots = rng.sample(TIME_SLOTS, k=rng.randint(1, 2))

            for time_slot in day_slots:
                # Each time slot has 2 products sold
                day_products = rng.sample(list(PRODUCTS.keys()), k=2)

                for product in day_products:
                    price = PRODUCTS[product]
                    quantity = _compute_quantity(
                        rng, product, temperature, weather, time_slot, store_id
                    )
                    rows.append(
                        {
                            "date": current.isoformat(),
                            "store_id": store_id,
                            "region": region,
                            "product": product,
                            "price": price,
                            "quantity": quantity,
                            "revenue": price * quantity,
                            "weather": weather,
                            "temperature": temperature,
                            "time_slot": time_slot,
                        }
                    )

        current += timedelta(days=1)

    return rows


def write_csv(
    rows: list[dict[str, str | int | float]], path: Path = OUTPUT_PATH
) -> None:
    """Write rows to CSV."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
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
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    rows = generate_sales_data()
    write_csv(rows)
    print(f"Generated {len(rows)} rows -> {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
