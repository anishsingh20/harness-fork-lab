# specs/

The Harness Runtime spec and the two helper scripts used in the tutorial.

## agents.yaml

One file describes the machine the agent runs on:

| Key | Value in this lab | Why |
| --- | --- | --- |
| `name` | `anish-fork-lab` | The session name you pass to every `doctl harness-runtime` command |
| `agent` | `claude-code` | Harness Runtime also supports `codex` and `opencode` |
| `size` | `mv-2vcpu-4gb` | The default sandbox. Fork C's pandas install is slow here; that is part of the comparison |
| `persistent_workspace` | `true` | Keep `/workspace` across pause and resume |
| `env.ANTHROPIC_BASE_URL` | `https://inference.do-ai.run` | Point Claude Code at DigitalOcean-hosted inference |
| `env.ANTHROPIC_MODEL` | `anthropic-claude-4.6-sonnet` | The model served at that endpoint |
| `secrets.ANTHROPIC_API_KEY` | `${DIGITALOCEAN_ACCESS_TOKEN}` | The same DigitalOcean token pays for the model. No Anthropic key needed |
| `permissions.default` | `allow` | Unattended experiment: the agent runs shell commands without asking. Use `ask` for your first session |
| `permissions.rules` | deny `rm -rf *` and `git push *` | The two commands an experiment must never run |

Change `name` if you want several people on one team to run the lab at the same time.

## start-session.py

```bash
python3 specs/start-session.py specs/agents.yaml
```

Why it exists: in `doctl` 1.168.0-beta, `doctl harness-runtime start` validates a Claude Code
spec's `ANTHROPIC_API_KEY` against Anthropic before creating the session. That check fails
when the key is a DigitalOcean token for DigitalOcean-hosted inference. The script reads the
spec, substitutes `${DIGITALOCEAN_ACCESS_TOKEN}`, and posts the manifest to
`POST /v2/agents/sessions` with `Content-Type: application/x-yaml`. The session it creates is
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
