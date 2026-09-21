# prompts/

The exact prompts sent in the tutorial, one file each, so you can send them with
[`specs/mars.py`](../specs/README.md#marspy) (`python3 specs/mars.py send <session> "$(cat prompts/<file>)"`),
paste them into the console chat, or type them into `doctl harness-runtime attach <session>`.
The order they are used in is in the [main README](../README.md#run-the-lab-on-harness-runtime).

| File | Sent to | Purpose |
| --- | --- | --- |
| [`01-setup.txt`](01-setup.txt) | parent, before the checkpoint | Clone, build `.venv`, run tests and benchmark, write `BRIEF.md`. The one turn you pay for once |
| [`02-fork-a-single-pass.txt`](02-fork-a-single-pass.txt) | Fork A | Rewrite every aggregation as one pass with dict accumulators |
| [`02-fork-b-profile-first.txt`](02-fork-b-profile-first.txt) | Fork B | Profile, fix only the hottest function, smallest possible diff |
| [`02-fork-c-pandas.txt`](02-fork-c-pandas.txt) | Fork C | Load orders into a DataFrame and use vectorised groupby |
| [`03-bad-experiment.txt`](03-bad-experiment.txt) | parent, after the forks | Deliberately breaks the rules (stray package, changed constant) so there is something to roll back |
| [`04-memory-check.txt`](04-memory-check.txt) | parent, after rollback | Shows that the machine came back and the conversation did not |

The three strategy prompts share the same framing. It tells the agent to read `BRIEF.md`
first (a fork has the setup turn's files but not its conversation), states the two hard
rules (15 tests pass, checksum `5c1322b035d743e3` unchanged), and asks for a summary in a
fixed shape so the three results line up side by side.
