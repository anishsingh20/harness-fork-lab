# harness-fork-lab

A small, deliberately slow Python service used in the DigitalOcean tutorial
*Checkpoint once, fork three ways: parallel agent experiments on Harness Runtime*.

`orders/report.py` builds the nightly orders report. It is correct and slow:
every aggregation rescans the full order list. The task handed to the agent
forks in the tutorial is to make `build_report` fast without changing a single
value in its output.

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pytest -q                 # 15 tests, all green on main
python bench.py           # 20,000 orders: prints the time and a checksum of the report
```

The checksum printed by `bench.py` and the golden file in `tests/` pin the
report's values. A faster `build_report` must keep both unchanged.
