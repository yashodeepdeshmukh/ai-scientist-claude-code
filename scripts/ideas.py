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
import json
import os
import re
import sys
import tempfile

from common import locked

REQUIRED = {"Name": str, "Title": str, "Experiment": str,
            "Interestingness": int, "Feasibility": int, "Novelty": int}


def load(path):
    with open(path) as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise SystemExit("ideas.json must be a JSON list")
    return data


def validate(ideas):
    errors, names = [], set()
    for i, idea in enumerate(ideas):
        if not isinstance(idea, dict):
            errors.append(f"#{i}: expected an idea object")
            continue
        tag = idea.get("Name", f"#{i}")
        for k, t in REQUIRED.items():
            if k not in idea:
                errors.append(f"{tag}: missing {k}")
            elif type(idea[k]) is not t:
                errors.append(f"{tag}: {k} should be {t.__name__}")
            elif t is int and not 1 <= idea[k] <= 10:
                errors.append(f"{tag}: {k} out of range 1-10")
        name = idea.get("Name", "")
        if isinstance(name, str) and not re.fullmatch(r"[a-z0-9_]+", name):
            errors.append(f"{tag}: Name must be lowercase letters, digits, underscores")
        if isinstance(name, str):
            if name in names:
                errors.append(f"{tag}: duplicate Name")
            names.add(name)
        if "novel" in idea and not isinstance(idea["novel"], bool):
            errors.append(f"{tag}: novel must be true/false")
    return errors


def save(path, ideas):
    errors = validate(ideas)
    if errors:
        raise SystemExit("\n".join(errors))
    with tempfile.NamedTemporaryFile(mode="w", dir=os.path.dirname(os.path.abspath(path)),
                                     delete=False) as staging:
        try:
            json.dump(ideas, staging, indent=4)
            staging.write("\n")
            staging.close()
            os.replace(staging.name, path)
        finally:
            if os.path.exists(staging.name):
                os.unlink(staging.name)


def update(path, name, fields):
    with locked(path):
        ideas = load(path)
        for idea in ideas:
            if idea.get("Name") == name:
                idea.update(fields)
                save(path, ideas)
                return
    raise SystemExit(f"No idea named {name}")


def select(ideas, limit, skip_novelty, include_seeds):
    errors = validate(ideas)
    if errors:
        raise SystemExit("\n".join(errors))
    statuses = {"pending", "seed"} if include_seeds else {"pending"}
    candidates = [
        idea for idea in ideas
        if idea.get("status", "pending") in statuses
        and (idea.get("novel") is True or (skip_novelty and "novel" not in idea))
    ]
    return sorted(
        candidates,
        key=lambda idea: (
            -(idea["Interestingness"] + idea["Feasibility"] + idea["Novelty"]),
            idea["Name"],
        ),
    )[:limit]


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("validate"); v.add_argument("path")
    ls = sub.add_parser("list"); ls.add_argument("path")
    ls.add_argument("--novel-only", action="store_true"); ls.add_argument("--unchecked", action="store_true")
    s = sub.add_parser("set"); s.add_argument("path"); s.add_argument("name"); s.add_argument("field"); s.add_argument("value")
    append = sub.add_parser("append")
    append.add_argument("path")
    append.add_argument("idea", type=json.loads)
    novelty = sub.add_parser("novelty")
    novelty.add_argument("path")
    novelty.add_argument("name")
    novelty.add_argument("verdict", choices=("true", "false"))
    novelty.add_argument("reason")
    picks = sub.add_parser("select")
    picks.add_argument("path")
    picks.add_argument("--limit", type=int, default=3)
    picks.add_argument("--skip-novelty", action="store_true")
    picks.add_argument("--include-seeds", action="store_true")
    a = ap.parse_args()

    if a.cmd == "set":
        try:
            value = json.loads(a.value)
        except json.JSONDecodeError:
            value = a.value
        update(a.path, a.name, {a.field: value})
        return
    if a.cmd == "append":
        with locked(a.path):
            ideas = load(a.path)
            save(a.path, [*ideas, a.idea])
        return
    if a.cmd == "novelty":
        update(a.path, a.name, {"novel": a.verdict == "true", "novelty_reason": a.reason})
        return
    ideas = load(a.path)
    if a.cmd == "select":
        if a.limit < 0:
            ap.error("--limit must be at least zero")
        print(json.dumps(select(ideas, a.limit, a.skip_novelty, a.include_seeds), indent=2))
        return
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
