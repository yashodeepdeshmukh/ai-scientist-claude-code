#!/usr/bin/env python3
"""Create the working folder for one idea and seed notes.txt with the baseline.

Usage: init_idea.py <exp_dir> <IdeaName>
Prints the new folder path: <exp_dir>/results/<YYYYmmdd_HHMMSS>_<IdeaName>
"""
import argparse
import datetime
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import copytree, read_means  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("exp_dir")
    ap.add_argument("name")
    a = ap.parse_args()

    with open(os.path.join(a.exp_dir, "ideas.json")) as f:
        ideas = json.load(f)
    idea = next((i for i in ideas if i.get("Name") == a.name), None)
    if idea is None:
        raise SystemExit(f"No idea named {a.name} in ideas.json")

    tdir = os.path.join(a.exp_dir, "template")
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    folder = os.path.join(a.exp_dir, "results", f"{stamp}_{a.name}")
    copytree(tdir, folder)
    with open(os.path.join(folder, "idea.json"), "w") as f:
        json.dump(idea, f, indent=4)

    baseline = read_means(os.path.join(tdir, "run_0"))
    with open(os.path.join(folder, "notes.txt"), "w") as f:
        f.write(f"# Title: {idea['Title']}\n")
        f.write(f"# Experiment description: {idea['Experiment']}\n")
        f.write("## Run 0: Baseline\n")
        f.write(f"Results: {json.dumps(baseline)}\n")
        f.write("Description: Baseline results.\n")
    print(os.path.abspath(folder))


if __name__ == "__main__":
    main()
