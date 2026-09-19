"""Deterministic synthetic order data for the nightly report.

The generator is seeded so every run, on every machine, produces the same
orders. Tests and the benchmark rely on that.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import datetime, timedelta

REGIONS = ("nyc", "sfo", "ams", "sgp", "blr", "fra")
STATUSES = ("paid", "paid", "paid", "paid", "refunded", "cancelled")
SKUS = tuple(f"SKU-{i:03d}" for i in range(1, 41))


@dataclass(frozen=True)
class Order:
    order_id: int
    customer_id: int
    sku: str
    quantity: int
    unit_price_cents: int
    region: str
    status: str
    placed_at: datetime

    @property
    def total_cents(self) -> int:
        return self.quantity * self.unit_price_cents


def generate_orders(n: int, seed: int = 42, customers: int | None = None) -> list[Order]:
    """Return ``n`` orders spread over 2025 for roughly ``n // 10`` customers."""
    rng = random.Random(seed)
    customers = customers or max(1, n // 10)
    start = datetime(2025, 1, 1)
    orders: list[Order] = []
    for i in range(n):
        orders.append(
            Order(
                order_id=100000 + i,
                customer_id=rng.randint(1, customers),
                sku=rng.choice(SKUS),
                quantity=rng.randint(1, 5),
                unit_price_cents=rng.choice((499, 999, 1499, 2999, 4999, 9999)),
                region=rng.choice(REGIONS),
                status=rng.choice(STATUSES),
                placed_at=start + timedelta(minutes=rng.randint(0, 365 * 24 * 60 - 1)),
            )
        )
    return orders
