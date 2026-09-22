# specs/

The Harness Runtime spec and the two helper scripts used in the tutorial. Back to the
[main README](../README.md#run-the-lab-on-harness-runtime) for the step-by-step lab, or to
[prompts/](../prompts/README.md) for what to send once the session is up.

## agents.yaml

One file describes the machine the agent runs on:

| Key | Value in this lab | Why |
| --- | --- | --- |
| `name` | `anish-fork-lab` | The session name you pass to every `doctl harness-runtime` command |
| `agent` | `claude-code` | Harness Runtime also supports `codex` and `opencode` |
| `size` | `mars-2vcpu-4gb` | The default sandbox (2 vCPUs, 4 GB). The lab ran when this shape was still called `mv-2vcpu-4gb`; the API now lists only `mars-*` slugs, see [sandbox sizes](https://docs.digitalocean.com/products/managed-agents/agent-harness-runtime/details/features/#sandbox-sizes) or `doctl harness-runtime sizes list`. Fork C's pandas install is slow here; that is part of the comparison |
| `persistent_workspace` | `true` | Keep `/workspace` across pause and resume |
| `env.ANTHROPIC_BASE_URL` | `https://inference.do-ai.run` | Point Claude Code at [DigitalOcean Serverless Inference](https://docs.digitalocean.com/products/inference/how-to/use-with-coding-agents/) |
| `env.ANTHROPIC_MODEL` | `anthropic-claude-4.6-sonnet` | One of the [models served at that endpoint](https://docs.digitalocean.com/products/inference/details/models/) |
| `secrets.ANTHROPIC_API_KEY` | `${DIGITALOCEAN_ACCESS_TOKEN}` | Your [DigitalOcean personal access token](https://docs.digitalocean.com/reference/api/create-personal-access-token/) pays for the model at [Serverless Inference rates](https://docs.digitalocean.com/products/inference/details/pricing/). No Anthropic key needed |
| `permissions.default` | `allow` | Unattended experiment: the agent runs shell commands without asking. Use `ask` for your first session |
| `permissions.rules` | deny `rm -rf *` and `git push *` | The two commands an experiment must never run |

Change `name` if you want several people on one team to run the lab at the same time.

## start-session.py

```bash
python3 specs/start-session.py specs/agents.yaml
```

Why it exists: in [`doctl`](https://docs.digitalocean.com/reference/doctl/) 1.168.0-beta ([beta releases](https://github.com/digitalocean/doctl/releases)), `doctl harness-runtime start` validates a Claude Code
spec's `ANTHROPIC_API_KEY` against Anthropic before creating the session. That check fails
when the key is a DigitalOcean token for DigitalOcean-hosted inference. The script reads the
spec, substitutes `${DIGITALOCEAN_ACCESS_TOKEN}`, and posts the manifest to
`POST /v2/agents/sessions` on the [DigitalOcean API](https://docs.digitalocean.com/reference/api/) with `Content-Type: application/x-yaml`. The session it creates is
identical to one made by `doctl harness-runtime start`.

The token comes from the `DIGITALOCEAN_ACCESS_TOKEN` environment variable, or, on macOS, from
`doctl`'s own config file if the variable is not set. It is never printed; error bodies are
redacted before they reach your terminal.

## mars.py

```bash
python3 specs/mars.py send <session> "prompt text" [--wait SECS]
python3 specs/mars.py tail <session> [--seconds SECS]
python3 specs/mars.py raw  <session> [--seconds SECS]
```

`send` posts one user turn to `/v2/agents/sessions/{id}/input`, then follows the session's
server-sent event stream and prints the agent's text and tool calls until the run emits
`run.completed`. `<session>` can be a name or a session ID. `tail` follows the stream without
sending anything; `raw` prints the SSE lines as they arrive, which is how the event shapes
in the script's docstring were discovered.

Because `send` returns when the run completes, you can start several in the background and
`wait` for all of them, which is how the three forks in the tutorial ran in parallel.

Requirements: Python 3.10+ and `curl` on your PATH (the stream is read through `curl` because
Python's `urllib` buffers SSE badly). Nothing to `pip install`.

You do not need either script to follow the tutorial. `doctl harness-runtime attach <session>`
gives you an interactive chat, and the console chat does the same in a browser. The scripts
are for when you want the prompts in files you can re-run.
