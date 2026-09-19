"""Time the nightly report and print a checksum of its output.

    python bench.py            # 20,000 orders, 1 run, prints the time
    python bench.py 6000 3     # custom size and run count (best of N)

The checksum must not change when you make the report faster. If it does,
the report's values changed and the optimisation is wrong.
"""
from __future__ import annotations

import hashlib
import json
import sys
import time

from orders import build_report, generate_orders


def checksum(report: dict) -> str:
    blob = json.dumps(report, sort_keys=True, default=str).encode()
    return hashlib.sha256(blob).hexdigest()[:16]


def main() -> None:
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 20000
    runs = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    orders = generate_orders(n)
    best = None
    report = None
    for _ in range(runs):
        t0 = time.perf_counter()
        report = build_report(orders)
        dt = time.perf_counter() - t0
        best = dt if best is None else min(best, dt)
    print(f"orders={n} runs={runs} best={best * 1000:.1f} ms checksum={checksum(report)}")


if __name__ == "__main__":
    main()
