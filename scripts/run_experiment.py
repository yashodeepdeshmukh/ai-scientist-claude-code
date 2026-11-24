#!/usr/bin/env python3
"""Run an experiment and preserve completed runs when resuming a workspace."""
import argparse
import datetime
import json
import os
import shutil
import sys

from common import locked, process_failure, read_means, run_cmd

MAX_RUNS = 5


def run_experiment(idea_dir, run_num, timeout):
    run_name = f"run_{run_num}"
    out = os.path.join(idea_dir, run_name)
    snapshot = os.path.join(idea_dir, f"{run_name}.py")
    with locked(os.path.join(idea_dir, "runs")):
        if os.path.exists(out):
            try:
                means = read_means(out)
            except (OSError, ValueError):
                shutil.rmtree(out)
            else:
                if not os.path.isfile(snapshot):
                    raise SystemExit(f"{run_name} has metrics but no code snapshot. Inspect the existing run.")
                print(f"Run {run_num} already completed.\nResults: {json.dumps(means, indent=2)}")
                return True

        shutil.copyfile(os.path.join(idea_dir, "experiment.py"), snapshot)
        code, _, _ = run_cmd([sys.executable, f"{run_name}.py", f"--out_dir={run_name}"],
                             idea_dir, timeout, capture=False)
        record = {"run": run_num, "time": datetime.datetime.now().isoformat(timespec="seconds")}
        if code:
            record["error"] = process_failure(code, timeout)
        else:
            try:
                record["means"] = read_means(out)
            except (OSError, ValueError):
                record["error"] = "Missing or invalid final_info.json"
        record["ok"] = "error" not in record
        with open(os.path.join(idea_dir, "runs.jsonl"), "a") as log:
            log.write(json.dumps(record) + "\n")

        if record["ok"]:
            print(f"Run {run_num} completed.\nResults: {json.dumps(record['means'], indent=2)}")
            return True
        if os.path.isdir(out):
            shutil.rmtree(out)
        os.unlink(snapshot)
        print(f"Run {run_num} failed. {record['error']}.", file=sys.stderr)
        return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("idea_dir")
    ap.add_argument("run_num", type=int)
    ap.add_argument("--timeout", type=int, default=7200)
    ap.add_argument("--max-stderr", type=int, help=argparse.SUPPRESS)
    ap.add_argument("--max-runs", type=int, default=MAX_RUNS)
    args = ap.parse_args()
    if not 1 <= args.run_num <= args.max_runs:
        ap.error(f"run_num must be in 1..{args.max_runs} (run_0 is the baseline)")
    return 0 if run_experiment(os.path.abspath(args.idea_dir), args.run_num, args.timeout) else 1


if __name__ == "__main__":
    sys.exit(main())
