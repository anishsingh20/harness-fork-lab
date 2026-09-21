# harness-fork-lab

[![tests](https://github.com/anishsingh20/harness-fork-lab/actions/workflows/tests.yml/badge.svg)](https://github.com/anishsingh20/harness-fork-lab/actions/workflows/tests.yml)

The sample repository for the DigitalOcean Community tutorial
**Checkpoint Once, Fork Three Ways: Parallel Agent Experiments on DigitalOcean Harness Runtime**
by [Anish Singh Walia](https://www.digitalocean.com/community/users/asinghwalia)
(Team Lead and Senior Technical Writer, DigitalOcean). It is the third article in a series on
[DigitalOcean Managed Agents](https://www.digitalocean.com/blog/managed-agents-runtime-services-private-preview),
after [Connecting AI Agents to SaaS Tools Without Sharing Your Credentials](https://www.digitalocean.com/community/tutorials/connect-tools-ai-agent-action-gateway)
and [The Agent Never Sees the Key](https://www.digitalocean.com/community/tutorials/credential-brokering-action-gateway).

It is a small, deliberately slow Python service plus everything needed to reproduce the lab
from the tutorial: the [Harness Runtime spec](specs/agents.yaml), two [helper scripts](specs/README.md),
the exact [prompts](prompts/README.md) sent to each agent, and a [script](scripts/compare.sh) that
checks every session from outside the agent.

**Contents:** [The problem](#the-problem-this-lab-is-about) ·
[What is in the repository](#what-is-in-the-repository) · [Rules of the game](#the-rules-of-the-game) ·
[Run it locally](#run-it-locally-no-agent-needed) · [Run the lab on Harness Runtime](#run-the-lab-on-harness-runtime) ·
[Results](#results-from-the-tutorial-run-19-september-2026) · [What a checkpoint carries](#what-a-checkpoint-does-and-does-not-carry) ·
[Further reading](#further-reading)

## The problem this lab is about

Every serious task you hand to a coding agent starts with the same setup: clone, create a
virtual environment, install dependencies, run the tests, record the baseline. That is fine
for one attempt. It is a tax when you want to compare three approaches, because you pay the
setup three times and hope nothing drifted in between.

DigitalOcean Managed Agents is two managed pieces: **Harness Runtime**, which runs your coding agent
(Claude Code, Codex CLI or OpenCode) on its own isolated Firecracker microVM, and **Action Gateway**,
which lets the agent act in other products without holding their credentials (the subject of the
two earlier tutorials). Harness Runtime has a feature for exactly this problem: **checkpoint-and-fork**. You save the agent's
whole sandbox at a known-good moment, fork that save point into independent copies, give each
copy a different instruction, and compare. If an experiment on the original session goes
wrong, you roll it back to the checkpoint in place.

```text
setup once (57 s)  ->  checkpoint (27 s)  ->  fork x3 (10.6 s)  ->  three strategies in parallel  ->  compare
                              ^
                              |  rollback (5.8 s) when the parent's next experiment goes wrong
```

## What is in the repository

| Path | What it is |
| --- | --- |
| [`orders/data.py`](orders/data.py) | `Order` dataclass and `generate_orders(n)`, a deterministic synthetic order generator |
| [`orders/report.py`](orders/report.py) | The nightly report. Correct, and slow on purpose: every aggregation rescans the full order list |
| [`bench.py`](bench.py) | Times `build_report` on 20,000 orders and prints a 16-character checksum of the output |
| [`tests/`](tests/) | 15 pytest tests plus a golden report for 500 orders. They pin the report's shape and values |
| [`specs/agents.yaml`](specs/agents.yaml) | The Harness Runtime spec: Claude Code on a `mv-2vcpu-4gb` sandbox with [DigitalOcean-hosted inference](https://docs.digitalocean.com/products/inference/how-to/use-with-coding-agents/). Every key is explained in [specs/README.md](specs/README.md#agentsyaml) |
| [`specs/start-session.py`](specs/start-session.py) | Creates the session by posting the spec to the Managed Agents API ([why](specs/README.md#start-sessionpy)) |
| [`specs/mars.py`](specs/mars.py) | Sends one prompt to a session and follows its event stream until the run completes ([usage](specs/README.md#marspy)) |
| [`prompts/`](prompts/) | The exact prompts used in the tutorial: setup, the three strategies, the bad experiment, the memory check ([index](prompts/README.md)) |
| [`scripts/compare.sh`](scripts/compare.sh) | Runs diff, tests and benchmark inside any number of sessions with `doctl harness-runtime exec` |
| [`pyproject.toml`](pyproject.toml) | pytest config so a bare `pytest -q` finds the `orders` package |
| [`.github/workflows/tests.yml`](.github/workflows/tests.yml) | Runs the 15 tests and a benchmark smoke test on Python 3.10 and 3.12 |

## The rules of the game

`build_report()` must get faster without changing a single value in its output. Two things
enforce that:

- [`pytest -q`](tests/test_report.py) runs 15 tests, including a [golden-file](tests/golden_report_500.json) comparison for 500 orders.
- [`python bench.py`](bench.py) prints a checksum of the full 20,000-order report. On `main` it is
  `5c1322b035d743e3`. A correct optimisation keeps it. A wrong one changes it.

## Run it locally (no agent needed)

```bash
git clone https://github.com/anishsingh20/harness-fork-lab
cd harness-fork-lab
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pytest -q                 # 15 passed
python bench.py           # orders=20000 runs=1 best=~4300 ms checksum=5c1322b035d743e3
python bench.py 20000 3   # best of three runs
```

Where the time goes: [`repeat_customer_share`](orders/report.py) alone is about 76% of the runtime because it
scans the full list once per customer. The other aggregations are O(n x k) for the same reason.

## Run the lab on Harness Runtime

You need:

- A DigitalOcean team with Managed Agents enabled. Request access on the
  [Managed Agents preview page](https://try.digitalocean.com/managed-agents-private-preview/); once enabled it
  appears in the console under [Managed Agents → Harness Runtime](https://cloud.digitalocean.com/managed-agents).
- A [personal access token](https://docs.digitalocean.com/reference/api/create-personal-access-token/) with full
  access, exported as `DIGITALOCEAN_ACCESS_TOKEN`.
- [`doctl`](https://docs.digitalocean.com/reference/doctl/) 1.168.0-beta or later. The `harness-runtime` (alias
  `agent`) commands are only in the beta builds on the [doctl releases page](https://github.com/digitalocean/doctl/releases).
  Run `doctl auth init`, then confirm with `doctl harness-runtime checkpoint --help`.
- No Anthropic key. The spec points Claude Code at
  [DigitalOcean Serverless Inference](https://docs.digitalocean.com/products/inference/), so the same token pays
  for the model ([pricing](https://docs.digitalocean.com/products/inference/details/pricing/),
  [available models](https://docs.digitalocean.com/products/inference/details/models/)).

Each step below links to the file it uses. Replace `<checkpoint-id>` and `<fork-N>` with the values `doctl` prints.

### 1. Start the parent session

```bash
doctl harness-runtime start --spec specs/agents.yaml
# if doctl rejects the DigitalOcean token as ANTHROPIC_API_KEY (1.168.0-beta does), use the API instead:
python3 specs/start-session.py specs/agents.yaml
```

Spec: [`specs/agents.yaml`](specs/agents.yaml). Why the fallback exists: [specs/README.md](specs/README.md#start-sessionpy).

### 2. Do the expensive setup once

```bash
python3 specs/mars.py send anish-fork-lab "$(cat prompts/01-setup.txt)"
```

Prompt: [`prompts/01-setup.txt`](prompts/01-setup.txt). You can paste it into the console chat or
`doctl harness-runtime attach anish-fork-lab` instead of using `mars.py`.

The agent clones this repository, builds `.venv`, runs the tests, records the baseline, and
writes `BRIEF.md` into the workspace. That file matters: forks and rolled-back sessions keep
the disk but start a fresh transcript, so anything the next agent needs to know goes in a file.

### 3. Checkpoint

```bash
doctl harness-runtime checkpoint create anish-fork-lab --label deps-installed-tests-green
```

### 4. Fork three ways

```bash
doctl harness-runtime fork anish-fork-lab --from-checkpoint <checkpoint-id> --count 3
```

Three `ready` sessions, each with the repository, the `.venv` and 15 green tests it never built
itself. Confirm from outside the agent with [`scripts/compare.sh`](scripts/compare.sh), which runs
`doctl harness-runtime exec` inside each sandbox:

```bash
scripts/compare.sh <fork-1> <fork-2> <fork-3>
```

### 5. One strategy per fork, in parallel

```bash
python3 specs/mars.py send <fork-1> "$(cat prompts/02-fork-a-single-pass.txt)" &
python3 specs/mars.py send <fork-2> "$(cat prompts/02-fork-b-profile-first.txt)" &
python3 specs/mars.py send <fork-3> "$(cat prompts/02-fork-c-pandas.txt)" &
wait
```

Prompts: [A, single pass](prompts/02-fork-a-single-pass.txt) · [B, profile first](prompts/02-fork-b-profile-first.txt) ·
[C, pandas](prompts/02-fork-c-pandas.txt). They share one framing; see [prompts/README.md](prompts/README.md).

### 6. Compare

```bash
scripts/compare.sh anish-fork-lab <fork-1> <fork-2> <fork-3>
```

### 7. Break the parent, then roll it back

```bash
python3 specs/mars.py send anish-fork-lab "$(cat prompts/03-bad-experiment.txt)"
scripts/compare.sh anish-fork-lab                          # red tests, changed checksum, stray package
doctl harness-runtime rollback anish-fork-lab <checkpoint-id>
scripts/compare.sh anish-fork-lab                          # back to the checkpoint state
python3 specs/mars.py send anish-fork-lab "$(cat prompts/04-memory-check.txt)"
```

Prompts: [`03-bad-experiment.txt`](prompts/03-bad-experiment.txt) (installs a stray package and changes a
constant so there is something to roll back) and [`04-memory-check.txt`](prompts/04-memory-check.txt) (shows the
machine came back and the conversation did not).

### 8. Clean up

```bash
doctl harness-runtime remove <fork-2>
doctl harness-runtime remove <fork-3>
doctl harness-runtime pause anish-fork-lab   # keep the winner until its patch is merged
```

## Results from the tutorial run (19 September 2026)

All four sandboxes were checked from a laptop with `doctl harness-runtime exec`, not by
asking the agents.

| Session | Strategy | Time (20,000 orders) | Speedup | Diff | New dependency | Tests | Checksum |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Parent | none (baseline) | 4,341.8 ms | 1x | 0 lines | no | 15 pass | `5c1322b035d743e3` |
| Fork A | single pass | **40.7 ms** | ~107x | +91 / -55, 1 file | no | 15 pass | `5c1322b035d743e3` |
| Fork B | profile first, minimal diff | 876.6 ms | ~5x | **+4 / -8, 1 file** | no | 15 pass | `5c1322b035d743e3` |
| Fork C | pandas | 64.9 ms | ~67x | +84 / -11, 2 files | pandas | 15 pass (0.23 s) | `5c1322b035d743e3` |

Timings: setup turn 57 s, checkpoint 27 s (84 GB sandbox image), fork to three `ready`
sessions 10.6 s, the three strategies finished in 49 s, 92 s and 187 s side by side, rollback
5.8 s. Which fork "wins" depends on what you optimise for: A if the nightly report is all
that matters, B if you want the smallest reviewable diff today, C only if the codebase
already lives in pandas.

## What a checkpoint does and does not carry

- Kept by fork and rollback: the workspace files, the `.venv` and every installed package,
  everything else on the sandbox disk. Rollback removed a package that git never tracked.
- Not kept: the agent's conversation. Each fork starts a fresh transcript, and the rolled-back
  parent answered "this is the start of our session". Put context on disk (`BRIEF.md`) before
  you checkpoint.

## Further reading

DigitalOcean Managed Agents

- [Announcement: DigitalOcean Managed Agents](https://www.digitalocean.com/blog/managed-agents-runtime-services-private-preview)
- [Request preview access](https://try.digitalocean.com/managed-agents-private-preview/)
- [Managed Agents in the console](https://cloud.digitalocean.com/managed-agents)
- [Tutorial 1: Connecting AI Agents to SaaS Tools Without Sharing Your Credentials using DigitalOcean Action Gateway](https://www.digitalocean.com/community/tutorials/connect-tools-ai-agent-action-gateway)
- [Tutorial 2: The Agent Never Sees the Key: Proving Credential Brokering in DigitalOcean Action Gateway](https://www.digitalocean.com/community/tutorials/credential-brokering-action-gateway)
- [All Community articles tagged managed-agents](https://www.digitalocean.com/community/tags/managed-agents)

Tools and APIs used here

- [`doctl` reference](https://docs.digitalocean.com/reference/doctl/) and [beta releases](https://github.com/digitalocean/doctl/releases) with the `harness-runtime` commands
- [DigitalOcean API reference](https://docs.digitalocean.com/reference/api/) and [creating a personal access token](https://docs.digitalocean.com/reference/api/create-personal-access-token/)
- [Serverless Inference](https://docs.digitalocean.com/products/inference/): [use with coding agents](https://docs.digitalocean.com/products/inference/how-to/use-with-coding-agents/), [models](https://docs.digitalocean.com/products/inference/details/models/), [pricing](https://docs.digitalocean.com/products/inference/details/pricing/)

In this repository

- [specs/README.md](specs/README.md): the spec, key by key, and the two helper scripts
- [prompts/README.md](prompts/README.md): which prompt goes to which session
- [scripts/compare.sh](scripts/compare.sh): verify any session from outside the agent

## License

MIT. See [LICENSE](LICENSE). The tutorial text and screenshots are published separately on the
[DigitalOcean Community](https://www.digitalocean.com/community/users/asinghwalia).
