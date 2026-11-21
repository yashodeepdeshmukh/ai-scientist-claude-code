#!/usr/bin/env python3
"""Create (or reuse) an experiment workspace and its baseline run.

Usage: init_workspace.py <template-name-or-path> [--workspace ai_scientist] [--rerun-baseline]

Layout produced (relative to the current directory):
  <workspace>/<exp>/template/          copy of the template
  <workspace>/<exp>/template/run_0/    baseline results (final_info.json)
  <workspace>/<exp>/ideas.json         created later by the idea generator
  <workspace>/<exp>/results/           one folder per idea
"""
import argparse
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import copytree, read_means, resolve_template, run_cmd  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("template")
    ap.add_argument("--workspace", default="ai_scientist")
    ap.add_argument("--rerun-baseline", action="store_true")
    ap.add_argument("--timeout", type=int, default=7200)
    args = ap.parse_args()

    src = resolve_template(args.template)
    exp = os.path.basename(os.path.normpath(src))
    exp_dir = os.path.abspath(os.path.join(args.workspace, exp))
    tdir = os.path.join(exp_dir, "template")
    os.makedirs(os.path.join(exp_dir, "results"), exist_ok=True)

    if not os.path.isdir(tdir):
        copytree(src, tdir)
    for required in ("experiment.py", "plot.py", "prompt.json", "seed_ideas.json", "latex/template.tex"):
        if not os.path.exists(os.path.join(tdir, required)):
            raise SystemExit(f"Template is missing required file: {required}")

    run0 = os.path.join(tdir, "run_0")
    if args.rerun_baseline and os.path.isdir(run0):
        shutil.rmtree(run0)
    if not os.path.exists(os.path.join(run0, "final_info.json")):
        print("Running baseline: python experiment.py --out_dir=run_0", file=sys.stderr)
        code, out, err = run_cmd([sys.executable, "experiment.py", "--out_dir=run_0"], tdir, args.timeout)
        if code != 0:
            print(err[-3000:], file=sys.stderr)
            raise SystemExit(f"Baseline run failed with exit code {code}")
        code, _, err = run_cmd([sys.executable, "plot.py"], tdir, 600)
        if code != 0:
            print(f"Warning: baseline plot failed: {err[-1000:]}", file=sys.stderr)

    print(json.dumps({
        "exp": exp,
        "exp_dir": exp_dir,
        "template_dir": tdir,
        "ideas_file": os.path.join(exp_dir, "ideas.json"),
        "baseline": read_means(run0),
    }, indent=2))


if __name__ == "__main__":
    main()
