#!/usr/bin/env sh
# Check one or more Harness Runtime sessions from outside the agent.
#
#   scripts/compare.sh anish-fork-lab <fork-1> <fork-2> <fork-3>
#
# For each session, runs inside its sandbox (via `doctl harness-runtime exec`):
#   git diff --shortstat        what the agent changed since the clone
#   pip show polars / pandas    stray or added packages
#   pytest -q (last line)       are the 15 tests still green
#   bench.py                    time and checksum on 20,000 orders
# The agent is not involved, so the answer does not depend on what it chose to report.
set -eu

if [ "$#" -eq 0 ]; then
  echo "usage: $0 <session> [<session> ...]" >&2
  exit 2
fi

WORKDIR=${WORKDIR:-/workspace/harness-fork-lab}
CHECK='git -c safe.directory="*" diff --shortstat;
for p in polars pandas; do
  if .venv/bin/pip show "$p" >/dev/null 2>&1; then echo "$p: installed"; else echo "$p: not installed"; fi
done;
.venv/bin/python -m pytest -q 2>&1 | tail -1;
.venv/bin/python bench.py'

for s in "$@"; do
  echo "== $s"
  doctl harness-runtime exec "$s" --workdir "$WORKDIR" -- sh -c "$CHECK"
done
