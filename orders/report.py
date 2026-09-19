"""Nightly orders report.

``build_report`` is the function the finance team runs every night. It works,
its output is correct, and it is slow: on the 20,000-order benchmark it takes
seconds because most of the aggregations rescan the full order list
for every customer, region, or order.

Do not change the shape or the values of the report. ``tests/`` pins both.
"""
from __future__ import annotations

from collections import defaultdict

from .data import Order

TOP_N = 10


def _paid(orders: list[Order]) -> list[Order]:
    return [o for o in orders if o.status == "paid"]


def revenue_by_region(orders: list[Order]) -> dict[str, int]:
    acc: dict[str, int] = {}
    for o in orders:
        if o.region not in acc:
            acc[o.region] = 0
        if o.status == "paid":
            acc[o.region] += o.total_cents
    return dict(sorted(acc.items()))


def monthly_revenue(orders: list[Order]) -> dict[str, int]:
    acc: dict[str, int] = {}
    for o in orders:
        key = o.placed_at.strftime("%Y-%m")
        if key not in acc:
            acc[key] = 0
        if o.status == "paid":
            acc[key] += o.total_cents
    return dict(sorted(acc.items()))


def top_customers(orders: list[Order], n: int = TOP_N) -> list[tuple[int, int]]:
    acc: dict[int, int] = {}
    for o in orders:
        if o.customer_id not in acc:
            acc[o.customer_id] = 0
        if o.status == "paid":
            acc[o.customer_id] += o.total_cents
    spend = sorted(acc.items(), key=lambda pair: (-pair[1], pair[0]))
    return spend[:n]


def repeat_customer_share(orders: list[Order]) -> float:
    """Share of paid orders that came from a customer with more than one paid order."""
    paid = _paid(orders)
    if not paid:
        return 0.0
    counts: dict[int, int] = defaultdict(int)
    for o in paid:
        counts[o.customer_id] += 1
    repeat = sum(1 for o in paid if counts[o.customer_id] > 1)
    return round(repeat / len(paid), 4)


def refund_rate(orders: list[Order]) -> float:
    if not orders:
        return 0.0
    refunded = sum(1 for o in orders if o.status == "refunded")
    return round(refunded / len(orders), 4)


def best_selling_skus(orders: list[Order], n: int = TOP_N) -> list[tuple[str, int]]:
    acc: dict[str, int] = {}
    for o in orders:
        if o.sku not in acc:
            acc[o.sku] = 0
        if o.status == "paid":
            acc[o.sku] += o.quantity
    counts = sorted(acc.items(), key=lambda pair: (-pair[1], pair[0]))
    return counts[:n]


def build_report(orders: list[Order]) -> dict:
    # Single pass to compute all aggregations at once
    region_rev: dict[str, int] = {}
    month_rev: dict[str, int] = {}
    customer_spend: dict[int, int] = {}
    sku_qty: dict[str, int] = {}
    paid_count = 0
    refunded_count = 0
    gross = 0
    paid_customer_counts: dict[int, int] = defaultdict(int)

    for o in orders:
        # region accumulator (all statuses contribute a zero entry)
        if o.region not in region_rev:
            region_rev[o.region] = 0
        # month accumulator
        month_key = o.placed_at.strftime("%Y-%m")
        if month_key not in month_rev:
            month_rev[month_key] = 0
        # customer accumulator
        if o.customer_id not in customer_spend:
            customer_spend[o.customer_id] = 0
        # sku accumulator
        if o.sku not in sku_qty:
            sku_qty[o.sku] = 0

        if o.status == "paid":
            region_rev[o.region] += o.total_cents
            month_rev[month_key] += o.total_cents
            customer_spend[o.customer_id] += o.total_cents
            sku_qty[o.sku] += o.quantity
            gross += o.total_cents
            paid_count += 1
            paid_customer_counts[o.customer_id] += 1
        elif o.status == "refunded":
            refunded_count += 1

    total = len(orders)

    # repeat_customer_share
    if paid_count == 0:
        rcs = 0.0
    else:
        repeat = sum(
            cnt for cid, cnt in paid_customer_counts.items() if cnt > 1
        )
        rcs = round(repeat / paid_count, 4)

    return {
        "orders": total,
        "paid_orders": paid_count,
        "gross_revenue_cents": gross,
        "average_order_cents": (gross // paid_count) if paid_count else 0,
        "refund_rate": round(refunded_count / total, 4) if total else 0.0,
        "repeat_customer_share": rcs,
        "revenue_by_region": dict(sorted(region_rev.items())),
        "monthly_revenue": dict(sorted(month_rev.items())),
        "top_customers": sorted(customer_spend.items(), key=lambda p: (-p[1], p[0]))[:TOP_N],
        "best_selling_skus": sorted(sku_qty.items(), key=lambda p: (-p[1], p[0]))[:TOP_N],
    }
