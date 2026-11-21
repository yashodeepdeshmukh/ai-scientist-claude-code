#!/usr/bin/env python3
"""Manage ideas.json (same schema as SakanaAI AI-Scientist).

Idea object: Name, Title, Experiment, Interestingness, Feasibility, Novelty (ints 1-10),
plus pipeline fields: novel (bool), novelty_reason (str), status (str).

Usage:
  ideas.py validate <ideas.json>
  ideas.py list <ideas.json> [--novel-only] [--unchecked]
  ideas.py set <ideas.json> <Name> <field> <json-value>
"""
import argparse
import contextlib
import fcntl
import json
import re
import sys

REQUIRED = {"Name": str, "Title": str, "Experiment": str,
            "Interestingness": int, "Feasibility": int, "Novelty": int}


@contextlib.contextmanager
def locked(path):
    """Exclusive lock so parallel agents can update different ideas safely."""
    with open(path + ".lock", "w") as lf:
        fcntl.flock(lf, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lf, fcntl.LOCK_UN)


def load(path):
    with open(path) as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise SystemExit("ideas.json must be a JSON list")
    return data


def validate(ideas):
    errors, names = [], set()
    for i, idea in enumerate(ideas):
        tag = idea.get("Name", f"#{i}")
        for k, t in REQUIRED.items():
            if k not in idea:
                errors.append(f"{tag}: missing {k}")
            elif not isinstance(idea[k], t):
                errors.append(f"{tag}: {k} should be {t.__name__}")
            elif t is int and not 1 <= idea[k] <= 10:
                errors.append(f"{tag}: {k} out of range 1-10")
        name = idea.get("Name", "")
        if isinstance(name, str) and not re.fullmatch(r"[a-z0-9_]+", name):
            errors.append(f"{tag}: Name must be lowercase letters, digits, underscores")
        if name in names:
            errors.append(f"{tag}: duplicate Name")
        names.add(name)
        if "novel" in idea and not isinstance(idea["novel"], bool):
            errors.append(f"{tag}: novel must be true/false")
    return errors


def set_field(a):
    ideas = load(a.path)
    for idea in ideas:
        if idea.get("Name") == a.name:
            try:
                idea[a.field] = json.loads(a.value)
            except json.JSONDecodeError:
                idea[a.field] = a.value
            with open(a.path, "w") as f:
                json.dump(ideas, f, indent=4)
            print(f"{a.name}.{a.field} = {idea[a.field]!r}")
            return
    raise SystemExit(f"No idea named {a.name}")



def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("validate"); v.add_argument("path")
    ls = sub.add_parser("list"); ls.add_argument("path")
    ls.add_argument("--novel-only", action="store_true"); ls.add_argument("--unchecked", action="store_true")
    s = sub.add_parser("set"); s.add_argument("path"); s.add_argument("name"); s.add_argument("field"); s.add_argument("value")
    a = ap.parse_args()

    if a.cmd == "set":
        with locked(a.path):
            set_field(a)
        return
    ideas = load(a.path)
    if a.cmd == "validate":
        errs = validate(ideas)
        print("\n".join(errs) if errs else f"OK: {len(ideas)} ideas")
        sys.exit(1 if errs else 0)
    if a.cmd == "list":
        for idea in ideas:
            if a.novel_only and idea.get("novel") is not True:
                continue
            if a.unchecked and "novel" in idea:
                continue
            print(f"{idea['Name']}\tI={idea.get('Interestingness')} F={idea.get('Feasibility')} "
                  f"N={idea.get('Novelty')}\tnovel={idea.get('novel', '?')}\tstatus={idea.get('status', '-')}\t{idea['Title']}")
        return


if __name__ == "__main__":
    main()
