import json
from datetime import datetime
from pathlib import Path

import pytest

from orders import Order, build_report, generate_orders
from orders.report import (
    best_selling_skus,
    monthly_revenue,
    refund_rate,
    repeat_customer_share,
    revenue_by_region,
    top_customers,
)

GOLDEN = Path(__file__).parent / "golden_report_500.json"


def order(oid, customer, sku="SKU-001", qty=1, price=1000, region="nyc", status="paid", month=1):
    return Order(
        order_id=oid,
        customer_id=customer,
        sku=sku,
        quantity=qty,
        unit_price_cents=price,
        region=region,
        status=status,
        placed_at=datetime(2025, month, 15, 12, 0),
    )


@pytest.fixture
def small():
    return [
        order(1, 1, qty=2, price=500, region="nyc", month=1),          # 1000 paid
        order(2, 1, qty=1, price=2000, region="sfo", month=2),         # 2000 paid
        order(3, 2, qty=3, price=1000, region="nyc", month=1),         # 3000 paid
        order(4, 3, qty=1, price=9999, region="ams", status="refunded", month=3),
        order(5, 4, qty=1, price=100, region="ams", status="cancelled", month=3),
        order(6, 2, sku="SKU-002", qty=4, price=250, region="sfo", month=2),  # 1000 paid
    ]


def test_generate_orders_is_deterministic():
    a = generate_orders(200, seed=1)
    b = generate_orders(200, seed=1)
    assert a == b
    assert len(a) == 200
    assert generate_orders(200, seed=2) != a


def test_revenue_by_region_counts_only_paid(small):
    assert revenue_by_region(small) == {"ams": 0, "nyc": 4000, "sfo": 3000}


def test_revenue_by_region_keys_are_sorted(small):
    assert list(revenue_by_region(small)) == ["ams", "nyc", "sfo"]


def test_monthly_revenue(small):
    assert monthly_revenue(small) == {"2025-01": 4000, "2025-02": 3000, "2025-03": 0}


def test_top_customers_orders_by_spend_then_id(small):
    assert top_customers(small) == [(2, 4000), (1, 3000), (3, 0), (4, 0)]


def test_top_customers_respects_n(small):
    assert top_customers(small, n=2) == [(2, 4000), (1, 3000)]


def test_top_customers_tie_breaks_on_lower_id():
    orders = [order(1, 9, price=1000), order(2, 3, price=1000)]
    assert top_customers(orders) == [(3, 1000), (9, 1000)]


def test_repeat_customer_share(small):
    # paid orders: c1, c1, c2, c2 -> all four are from repeat customers
    assert repeat_customer_share(small) == 1.0


def test_repeat_customer_share_single_orders():
    orders = [order(1, 1), order(2, 2), order(3, 3), order(4, 3)]
    assert repeat_customer_share(orders) == 0.5


def test_repeat_customer_share_empty():
    assert repeat_customer_share([]) == 0.0
    assert repeat_customer_share([order(1, 1, status="cancelled")]) == 0.0


def test_refund_rate(small):
    assert refund_rate(small) == round(1 / 6, 4)
    assert refund_rate([]) == 0.0


def test_best_selling_skus(small):
    assert best_selling_skus(small) == [("SKU-001", 6), ("SKU-002", 4)]


def test_build_report_shape_and_totals(small):
    report = build_report(small)
    assert report["orders"] == 6
    assert report["paid_orders"] == 4
    assert report["gross_revenue_cents"] == 7000
    assert report["average_order_cents"] == 1750
    assert set(report) == {
        "orders",
        "paid_orders",
        "gross_revenue_cents",
        "average_order_cents",
        "refund_rate",
        "repeat_customer_share",
        "revenue_by_region",
        "monthly_revenue",
        "top_customers",
        "best_selling_skus",
    }


def test_build_report_empty():
    report = build_report([])
    assert report["orders"] == 0
    assert report["average_order_cents"] == 0
    assert report["top_customers"] == []


def test_build_report_matches_golden():
    """Any optimisation must reproduce this report byte for byte."""
    report = build_report(generate_orders(500, seed=7))
    expected = json.loads(GOLDEN.read_text())
    got = json.loads(json.dumps(report, sort_keys=True, default=str))
    assert got == expected
