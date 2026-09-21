#!/usr/bin/env python3
"""Create the session in agents.yaml via the DigitalOcean Managed Agents API.

`doctl agent start` validates ANTHROPIC_API_KEY against Anthropic for
claude-code specs. This spec uses DigitalOcean-hosted inference, so we post
the manifest to the sessions API directly with the token already in doctl.
"""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SPEC_PATH = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT / "agents.yaml"
API = "https://api.digitalocean.com/v2/agents/sessions"
CFG = Path.home() / "Library/Application Support/doctl/config.yaml"


def doctl_token() -> str:
    env = os.environ.get("DIGITALOCEAN_ACCESS_TOKEN", "").strip()
    if env:
        return env
    text = CFG.read_text()
    ctx = None
    m = re.search(r"(?m)^context:\s*(\S+)", text)
    if m:
        ctx = m.group(1)
    for key in (ctx, "onboarding"):
        if not key:
            continue
        m = re.search(rf"(?m)^  {re.escape(key)}:\s*(\S+)", text)
        if m:
            return m.group(1)
    m = re.search(r"(?m)^access-token:\s*(\S+)", text)
    if m:
        return m.group(1)
    sys.exit("No doctl token found. Run: doctl auth init")


def manifest(token: str) -> str:
    spec = SPEC_PATH.read_text()
    if "ANTHROPIC_API_KEY:" not in spec:
        spec = spec.replace(
            "secrets:\n",
            'secrets:\n  ANTHROPIC_API_KEY: "${DIGITALOCEAN_ACCESS_TOKEN}"\n',
            1,
        )
    return spec.replace("${DIGITALOCEAN_ACCESS_TOKEN}", token)


def main() -> None:
    token = doctl_token()
    body = manifest(token)
    req = urllib.request.Request(
        API,
        data=body.encode(),
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "Content-Type": "application/x-yaml",
        },
    )
    print(f"Creating session from {SPEC_PATH.name} (API, not doctl start)...")
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode()
        print(raw.replace(token, "<token>"), file=sys.stderr)
        sys.exit(exc.code)
    session = data.get("session") or {}
    if not session:
        print(json.dumps(data, indent=2).replace(token, "<token>"))
        sys.exit(1)
    print(f"Session  {session.get('name')}")
    print(f"Agent    {session.get('agent_kind')}")
    print(f"Status   {session.get('status')}")
    print(f"ID       {session.get('session_id')}")
    for w in data.get("warnings", []) or []:
        print(f"Warning  {w}")
    print()
    print("Next step")
    print(f"  doctl agent attach {session.get('name')}")


if __name__ == "__main__":
    main()
