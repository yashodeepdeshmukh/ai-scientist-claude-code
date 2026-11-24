#!/usr/bin/env python3
"""Run python plot.py inside the idea folder and list the figures it produced.

Usage: run_plot.py <idea_dir> [--timeout 600]
"""
import argparse
import glob
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import process_failure, run_cmd  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("idea_dir")
    ap.add_argument("--timeout", type=int, default=600)
    a = ap.parse_args()
    d = os.path.abspath(a.idea_dir)
    code, _, _ = run_cmd([sys.executable, "plot.py"], d, a.timeout, capture=False)
    if code != 0:
        print(f"Plotting failed. {process_failure(code, a.timeout)}.", file=sys.stderr)
        sys.exit(1)
    figs = sorted(os.path.basename(p) for p in glob.glob(os.path.join(d, "*.png")))
    print("Plotting OK. Figures:\n" + "\n".join(figs))


if __name__ == "__main__":
    main()
