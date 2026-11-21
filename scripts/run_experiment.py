#!/usr/bin/env python3
"""Run one experiment: python experiment.py --out_dir=run_<n> inside the idea folder.

Usage: run_experiment.py <idea_dir> <run_num> [--timeout 7200] [--max-stderr 1500]

On success: snapshots experiment.py as run_<n>.py, appends to runs.jsonl, prints the metric means.
On failure: deletes run_<n>/, prints the stderr tail, exits non-zero (retry the SAME run number).
Mirrors MAX_RUNS / MAX_STDERR_OUTPUT behaviour of AI-Scientist's perform_experiments.py.
"""
import argparse
import datetime
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import read_means, run_cmd  # noqa: E402

MAX_RUNS = 5


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("idea_dir")
    ap.add_argument("run_num", type=int)
    ap.add_argument("--timeout", type=int, default=7200)
    ap.add_argument("--max-stderr", type=int, default=1500)
    ap.add_argument("--max-runs", type=int, default=MAX_RUNS)
    a = ap.parse_args()

    if not 1 <= a.run_num <= a.max_runs:
        raise SystemExit(f"run_num must be in 1..{a.max_runs} (run_0 is the baseline)")
    d = os.path.abspath(a.idea_dir)
    out = f"run_{a.run_num}"
    if os.path.exists(os.path.join(d, out)):
        shutil.rmtree(os.path.join(d, out))

    code, stdout, stderr = run_cmd([sys.executable, "experiment.py", f"--out_dir={out}"], d, a.timeout)
    ok = code == 0 and os.path.exists(os.path.join(d, out, "final_info.json"))
    record = {"run": a.run_num, "time": datetime.datetime.now().isoformat(timespec="seconds"), "ok": ok}

    if not ok:
        if os.path.isdir(os.path.join(d, out)):
            shutil.rmtree(os.path.join(d, out))
        tail = stderr[-a.max_stderr:] if stderr else stdout[-a.max_stderr:]
        record["error"] = tail
        with open(os.path.join(d, "runs.jsonl"), "a") as f:
            f.write(json.dumps(record) + "\n")
        msg = "Run timed out" if code == 124 else f"Run failed with exit code {code}"
        print(f"{msg}.\nSTDERR (last {a.max_stderr} chars):\n{tail}")
        sys.exit(1)

    shutil.copy(os.path.join(d, "experiment.py"), os.path.join(d, f"{out}.py"))
    means = read_means(os.path.join(d, out))
    record["means"] = means
    with open(os.path.join(d, "runs.jsonl"), "a") as f:
        f.write(json.dumps(record) + "\n")
    print(f"Run {a.run_num} completed.\nResults: {json.dumps(means, indent=2)}")


if __name__ == "__main__":
    main()
