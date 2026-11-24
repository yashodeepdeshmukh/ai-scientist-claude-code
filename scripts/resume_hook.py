#!/usr/bin/env python3
"""Connect Claude Code lifecycle events to the local research store."""
import json
import os
from pathlib import Path
import re
import shlex
import sqlite3
import sys

from research_state import interrupt, session_context


def main():
    raw = sys.stdin.read()
    if raw.strip():
        try:
            payload = json.loads(raw)
        except ValueError:
            return
    elif sys.argv[1:] == ["SessionStart"]:
        # The hook's configured matcher has already identified the event.
        payload = {
            "hook_event_name": "SessionStart",
            "session_id": os.environ.get("CLAUDE_CODE_SESSION_ID"),
            "cwd": os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd(),
        }
    else:
        return
    if not isinstance(payload, dict):
        return

    event = payload.get("hook_event_name")
    session_id = payload.get("session_id")
    cwd = os.environ.get("CLAUDE_PROJECT_DIR") or payload.get("cwd")
    if not isinstance(session_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", session_id):
        return
    if not isinstance(cwd, str) or not Path(cwd).is_absolute():
        return

    if event == "SessionStart":
        env_file = os.environ.get("CLAUDE_ENV_FILE")
        if env_file:
            path = Path(env_file)
            path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as stream:
                stream.write(f"\nexport AI_SCIENTIST_SESSION_ID={session_id}\n")
                stream.write(f"export AI_SCIENTIST_PROJECT_DIR={shlex.quote(cwd)}\n")

        context = session_context(cwd, session_id)
        if context:
            print(json.dumps({
                "hookSpecificOutput": {
                    "hookEventName": "SessionStart",
                    "additionalContext": context,
                },
            }))
    elif event == "StopFailure" and payload.get("error") == "rate_limit":
        interrupt(session_id, cwd, "rate_limit")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, sqlite3.Error) as exc:
        print(f"AI Scientist research hook: {exc}", file=sys.stderr)
