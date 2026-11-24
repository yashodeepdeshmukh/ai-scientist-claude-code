#!/usr/bin/env python3
"""Create the working folder for one idea and seed notes.txt with the baseline.

Usage: init_idea.py <exp_dir> <IdeaName> [--resume]
Prints the new or existing idea folder path.
"""
import argparse
import datetime
import json
import os
import re
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import copytree, locked, read_means  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("exp_dir")
    ap.add_argument("name")
    ap.add_argument("--resume", action="store_true")
    a = ap.parse_args()
    if not re.fullmatch(r"[a-z0-9_]+", a.name):
        ap.error("Idea name must contain only lowercase letters, digits and underscores")

    with open(os.path.join(a.exp_dir, "ideas.json")) as f:
        ideas = json.load(f)
    idea = next((i for i in ideas if i.get("Name") == a.name), None)
    if idea is None:
        raise SystemExit(f"No idea named {a.name} in ideas.json")

    exp_dir = os.path.abspath(a.exp_dir)
    results = os.path.join(exp_dir, "results")
    os.makedirs(results, exist_ok=True)
    with locked(os.path.join(exp_dir, "workspace")):
        if a.resume:
            pattern = re.compile(r"\d{8}_\d{6}(?:_\d{6})?_" + re.escape(a.name))
            matches = sorted(name for name in os.listdir(results) if pattern.fullmatch(name))
            for name in reversed(matches):
                candidate = os.path.join(results, name)
                if os.path.isfile(os.path.join(candidate, "idea.json")):
                    print(candidate)
                    return
        print(create_idea_folder(exp_dir, results, idea))


def create_idea_folder(exp_dir, results, idea):
    tdir = os.path.join(exp_dir, "template")
    baseline = read_means(os.path.join(tdir, "run_0"))
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    folder = os.path.join(results, f"{stamp}_{idea['Name']}")
    with tempfile.TemporaryDirectory(dir=results) as staging:
        candidate = os.path.join(staging, "idea")
        copytree(tdir, candidate)
        with open(os.path.join(candidate, "idea.json"), "w") as f:
            json.dump(idea, f, indent=4)
        with open(os.path.join(candidate, "notes.txt"), "w") as f:
            f.write(f"# Title: {idea['Title']}\n")
            f.write(f"# Experiment description: {idea['Experiment']}\n")
            f.write("## Run 0: Baseline\n")
            f.write(f"Results: {json.dumps(baseline)}\n")
            f.write("Description: Baseline results.\n")
        os.rename(candidate, folder)
    return folder


if __name__ == "__main__":
    main()
