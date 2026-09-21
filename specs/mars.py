#!/usr/bin/env python3
"""Small driver for the Managed Agents sessions API.

    python3 specs/mars.py send <session> "prompt text" [--wait SECS]
    python3 specs/mars.py tail <session> [--seconds SECS]
    python3 specs/mars.py raw  <session> [--seconds SECS]      # raw SSE lines

`send` posts one user turn to /v2/agents/sessions/{id}/input, then follows the
event stream and prints the agent's text and tool calls until the run that the
POST returned emits `run.completed` (or the wait expires). <session> may be a
session name or a session ID.

Event stream shape (observed 2026-09-19):
    run.started            data.agent = the prompt
    run.token_delta        data.text, data.is_reasoning
    run.tool_call_started  data.name, data.input.command
    run.tool_call_completed data.ok, data.duration_ms, data.summary
    run.completed          data.total_tokens_in/out, run_cost_micros
    run.log                data.message ("session_idle_awaiting_user", ...)
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

API = "https://api.digitalocean.com/v2/agents/sessions"
CFG = Path.home() / "Library/Application Support/doctl/config.yaml"


def token() -> str:
    env = os.environ.get("DIGITALOCEAN_ACCESS_TOKEN", "").strip()
    if env:
        return env
    text = CFG.read_text()
    m = re.search(r"(?m)^context:\s*(\S+)", text)
    ctx = m.group(1) if m else None
    for key in (ctx, "onboarding"):
        if key:
            m = re.search(rf"(?m)^  {re.escape(key)}:\s*(\S+)", text)
            if m:
                return m.group(1)
    m = re.search(r"(?m)^access-token:\s*(\S+)", text)
    if m:
        return m.group(1)
    sys.exit("No doctl token found. Run: doctl auth init")


TOKEN = token()
UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")


def resolve(session: str) -> str:
    if UUID.match(session):
        return session
    out = subprocess.run(
        ["doctl", "harness-runtime", "show", session, "-o", "json"],
        capture_output=True, text=True, check=True,
    ).stdout
    return json.loads(out)["session_id"]


def post(path: str, body: dict) -> dict:
    req = urllib.request.Request(
        f"{API}/{path}", data=json.dumps(body).encode(), method="POST",
        headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json",
                 "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read().decode()
            return json.loads(raw) if raw.strip() else {}
    except urllib.error.HTTPError as exc:
        sys.exit(f"HTTP {exc.code}: {exc.read().decode()}")


def stream(session_id: str, seconds: float, raw: bool = False):
    """Follow the SSE stream via curl (urllib buffers SSE badly). Yields parsed events."""
    cmd = [
        "curl", "-sN", "--max-time", str(int(seconds)),
        f"{API}/{session_id}/events?stream=true",
        "-H", f"Authorization: Bearer {TOKEN}", "-H", "Accept: text/event-stream",
    ]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, text=True, bufsize=1)
    assert proc.stdout is not None
    for line in proc.stdout:
        line = line.rstrip("\n")
        if raw:
            print(line)
            continue
        if line.startswith("data:"):
            try:
                yield json.loads(line[5:].strip())
            except json.JSONDecodeError:
                yield {"type": "_raw", "data": {"text": line}}
    proc.wait()


class Printer:
    """Turns the token stream into readable lines: agent text, tool calls, results."""

    def __init__(self, run_id: str | None = None, t0: float | None = None):
        self.run_id = run_id
        self.t0 = t0 or time.time()
        self.buf = ""

    def flush(self) -> None:
        if self.buf.strip():
            for ln in self.buf.strip("\n").split("\n"):
                print(f"{'':8s} [agent] {ln}")
        self.buf = ""

    def handle(self, ev: dict) -> bool:
        """Print the event. Return True when the watched run is finished."""
        if self.run_id and ev.get("run_id") not in (self.run_id, ""):
            # Skip catch-up history from earlier runs, but still print nothing.
            if ev.get("type") != "stream.state":
                return False
        t = ev.get("type", "")
        d = ev.get("data") or {}
        el = f"{time.time() - self.t0:6.1f}s"
        if t == "run.token_delta":
            if not d.get("is_reasoning"):
                self.buf += d.get("text", "")
            return False
        self.flush()
        if t == "run.started":
            print(f"{el} [run  ] started: {d.get('agent', '')[:120]}")
        elif t == "run.tool_call_started":
            inp = d.get("input") or {}
            desc = inp.get("command") or inp.get("file_path") or inp.get("pattern") or json.dumps(inp)[:160]
            print(f"{el} [tool ] {d.get('name')}: {desc}")
        elif t == "run.tool_call_completed":
            summary = (d.get("summary") or "").strip().replace("\n", "\n" + " " * 17)
            ok = "ok" if d.get("ok") else "FAIL"
            print(f"{el} [done ] {ok} {d.get('duration_ms', 0)} ms  {summary[:600]}")
        elif t == "run.completed":
            print(f"{el} [run  ] completed: in={d.get('total_tokens_in')} out={d.get('total_tokens_out')} "
                  f"cost=${d.get('run_cost_micros', 0) / 1e6:.4f}")
            return True
        elif t == "run.failed" or t.endswith(".error"):
            print(f"{el} [ERROR] {json.dumps(d)[:400]}")
            return True
        elif t == "run.log":
            msg = d.get("message", "")
            if msg and msg != "session_idle_awaiting_user":
                print(f"{el} [log  ] {msg}")
        return False


def main() -> None:
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    cmd, session = sys.argv[1], sys.argv[2]
    sid = resolve(session)
    secs = 600.0
    for i, a in enumerate(sys.argv):
        if a in ("--wait", "--seconds") and i + 1 < len(sys.argv):
            secs = float(sys.argv[i + 1])
    if cmd == "send":
        text = sys.argv[3]
        t0 = time.time()
        r = post(f"{sid}/input", {"text": text})
        run_id = r.get("run_id")
        print(f"sent to {session} ({sid[:8]}) run {run_id} at {time.strftime('%H:%M:%SZ', time.gmtime())}")
        p = Printer(run_id, t0)
        for ev in stream(sid, secs):
            if p.handle(ev):
                break
        else:
            p.flush()
            print(f"stopped waiting after {secs:.0f}s (run may still be going)")
    elif cmd == "tail":
        p = Printer(None)
        for ev in stream(sid, secs):
            p.handle(ev)
        p.flush()
    elif cmd == "raw":
        for _ in stream(sid, secs, raw=True):
            pass
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
