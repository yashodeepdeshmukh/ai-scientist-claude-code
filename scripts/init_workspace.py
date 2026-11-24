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
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import copytree, locked, process_failure, read_means, resolve_template, run_cmd  # noqa: E402
from ideas import load, save


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
    if os.path.commonpath((os.path.realpath(src), os.path.realpath(exp_dir))) == os.path.realpath(src):
        raise SystemExit("Choose a workspace outside the source template directory")
    os.makedirs(os.path.join(exp_dir, "results"), exist_ok=True)

    with locked(os.path.join(exp_dir, "workspace")):
        if not os.path.isdir(tdir):
            with tempfile.TemporaryDirectory(dir=exp_dir) as staging:
                template = os.path.join(staging, "template")
                copytree(src, template)
                check_template(template)
                os.rename(template, tdir)
        check_template(tdir)

        run0 = os.path.join(tdir, "run_0")
        baseline = None
        if not args.rerun_baseline:
            try:
                baseline = read_means(run0)
                check_checkpoint(tdir, run0)
            except (OSError, ValueError):
                baseline = None
        if baseline is None:
            baseline = run_baseline(tdir, run0, args.timeout)

    ideas_file = os.path.join(exp_dir, "ideas.json")
    with locked(ideas_file):
        if not os.path.exists(ideas_file):
            seeds = load(os.path.join(tdir, "seed_ideas.json"))
            save(ideas_file, [dict(idea, status="seed") for idea in seeds])

    print(json.dumps({
        "exp": exp,
        "exp_dir": exp_dir,
        "template_dir": tdir,
        "ideas_file": ideas_file,
        "baseline": baseline,
    }, indent=2))


def check_template(tdir):
    for required in ("experiment.py", "plot.py", "prompt.json", "seed_ideas.json", "latex/template.tex"):
        if not os.path.isfile(os.path.join(tdir, required)):
            raise SystemExit(f"Template is missing required file: {required}")


def check_checkpoint(tdir, run0):
    if os.path.isfile(os.path.join(tdir, "benchmark_evaluator.py")):
        if not os.path.isfile(os.path.join(run0, "checkpoint.npz")):
            raise FileNotFoundError("Baseline did not write checkpoint.npz")


def run_baseline(tdir, run0, timeout):
    print("Running baseline: python experiment.py --out_dir=run_0", file=sys.stderr)
    with tempfile.TemporaryDirectory(dir=tdir) as staging:
        previous = os.path.join(staging, "previous")
        if os.path.lexists(run0):
            os.rename(run0, previous)
        try:
            code, _, _ = run_cmd([sys.executable, "experiment.py", "--out_dir=run_0"],
                                 tdir, timeout, capture=False)
            if code != 0:
                raise SystemExit(f"Baseline failed. {process_failure(code, timeout)}.")
            try:
                baseline = read_means(run0)
                check_checkpoint(tdir, run0)
            except FileNotFoundError as error:
                if error.filename:
                    raise SystemExit("Baseline failed. Missing final_info.json.") from None
                raise SystemExit(f"Baseline failed. {error}.") from None
            except (OSError, ValueError):
                raise SystemExit("Baseline failed. Missing or invalid final_info.json.") from None
        except BaseException:
            if os.path.isdir(run0) and not os.path.islink(run0):
                shutil.rmtree(run0)
            elif os.path.lexists(run0):
                os.unlink(run0)
            if os.path.lexists(previous):
                os.rename(previous, run0)
            raise

    code, _, _ = run_cmd([sys.executable, "plot.py"], tdir, 600, capture=False)
    if code != 0:
        print(f"Baseline plot failed. {process_failure(code, 600)}.", file=sys.stderr)
    return baseline


if __name__ == "__main__":
    main()
