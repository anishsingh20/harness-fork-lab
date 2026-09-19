"""Nightly orders report.

``build_report`` is the function the finance team runs every night. It works,
its output is correct, and it is slow: on the 20,000-order benchmark it takes
seconds because most of the aggregations rescan the full order list
for every customer, region, or order.

Do not change the shape or the values of the report. ``tests/`` pins both.
"""
from __future__ import annotations

from .data import Order

TOP_N = 10


def _paid(orders: list[Order]) -> list[Order]:
    return [o for o in orders if o.status == "paid"]


def revenue_by_region(orders: list[Order]) -> dict[str, int]:
    regions = sorted({o.region for o in orders})
    out: dict[str, int] = {}
    for region in regions:
        total = 0
        for o in orders:
            if o.region == region and o.status == "paid":
                total += o.total_cents
        out[region] = total
    return out


def monthly_revenue(orders: list[Order]) -> dict[str, int]:
    months = sorted({o.placed_at.strftime("%Y-%m") for o in orders})
    out: dict[str, int] = {}
    for month in months:
        total = 0
        for o in orders:
            if o.status == "paid" and o.placed_at.strftime("%Y-%m") == month:
                total += o.total_cents
        out[month] = total
    return out


def top_customers(orders: list[Order], n: int = TOP_N) -> list[tuple[int, int]]:
    customers = sorted({o.customer_id for o in orders})
    spend: list[tuple[int, int]] = []
    for customer in customers:
        total = 0
        for o in orders:
            if o.customer_id == customer and o.status == "paid":
                total += o.total_cents
        spend.append((customer, total))
    spend.sort(key=lambda pair: (-pair[1], pair[0]))
    return spend[:n]


def repeat_customer_share(orders: list[Order]) -> float:
    """Share of paid orders that came from a customer with more than one paid order."""
    paid = _paid(orders)
    if not paid:
        return 0.0
    repeat = 0
    for o in paid:
        count = 0
        for other in paid:
            if other.customer_id == o.customer_id:
                count += 1
        if count > 1:
            repeat += 1
    return round(repeat / len(paid), 4)


def refund_rate(orders: list[Order]) -> float:
    if not orders:
        return 0.0
    refunded = len([o for o in orders if o.status == "refunded"])
    return round(refunded / len(orders), 4)


def best_selling_skus(orders: list[Order], n: int = TOP_N) -> list[tuple[str, int]]:
    skus = sorted({o.sku for o in orders})
    counts: list[tuple[str, int]] = []
    for sku in skus:
        qty = 0
        for o in orders:
            if o.sku == sku and o.status == "paid":
                qty += o.quantity
        counts.append((sku, qty))
    counts.sort(key=lambda pair: (-pair[1], pair[0]))
    return counts[:n]


def build_report(orders: list[Order]) -> dict:
    paid = _paid(orders)
    gross = sum(o.total_cents for o in paid)
    return {
        "orders": len(orders),
        "paid_orders": len(paid),
        "gross_revenue_cents": gross,
        "average_order_cents": (gross // len(paid)) if paid else 0,
        "refund_rate": refund_rate(orders),
        "repeat_customer_share": repeat_customer_share(orders),
        "revenue_by_region": revenue_by_region(orders),
        "monthly_revenue": monthly_revenue(orders),
        "top_customers": top_customers(orders),
        "best_selling_skus": best_selling_skus(orders),
    }
