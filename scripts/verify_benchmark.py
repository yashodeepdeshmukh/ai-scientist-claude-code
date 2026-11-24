#!/usr/bin/env python3
"""Independently score a baseline and selected candidate using the template evaluator."""
import argparse
import hashlib
import json
from pathlib import Path
import re
from statistics import mean
import sys
from tempfile import NamedTemporaryFile

from common import locked, process_failure, run_cmd

REPORT = "benchmark_results.json"
TABLE = "benchmark_results.tex"
TABLE_INPUT = r"\input{../benchmark_results.tex}"
SCHEMA = 1


def evaluator_for(folder):
    path = folder.parent.parent / "template" / "benchmark_evaluator.py"
    return path if path.is_file() else None


def digest(path):
    with path.open("rb") as file:
        result = hashlib.sha256()
        for chunk in iter(lambda: file.read(1048576), b""):
            result.update(chunk)
    return result.hexdigest()


def atomic_write(path, value):
    with NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as output:
        temporary = Path(output.name)
        try:
            output.write(value)
            output.close()
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)


def inputs(folder, evaluator):
    runs = sorted(
        (path for path in folder.iterdir()
         if re.fullmatch(r"run_[1-9][0-9]*", path.name) and path.is_dir()
         and path.with_suffix(".py").is_file() and (path / "final_info.json").is_file()),
        key=lambda path: int(path.name.removeprefix("run_")),
    )
    if not runs:
        raise ValueError("No completed candidate runs to benchmark")
    checkpoints = {}
    for run in [folder / "run_0", *runs]:
        path = run / "checkpoint.npz"
        if run.is_symlink() or path.is_symlink() or not path.is_file():
            raise ValueError(f"{run.name} is missing a regular checkpoint.npz")
        checkpoints[run.name] = digest(path)
    return {"evaluator_sha256": digest(evaluator), "checkpoint_sha256": checkpoints}


def score(evaluator, folder, run, split, timeout):
    code, output, _ = run_cmd(
        [sys.executable, str(evaluator), str(folder / run / "checkpoint.npz"), "--split", split],
        evaluator.parent, timeout,
    )
    if code:
        raise ValueError(f"{run} {split} evaluation failed. {process_failure(code, timeout)}.")
    try:
        scores = json.loads(output)
        score_keys(scores)
    except (TypeError, ValueError, AttributeError):
        raise ValueError(f"{run} {split} evaluation returned invalid accuracy scores") from None
    return scores


def score_keys(scores):
    if not isinstance(scores, dict) or not scores:
        raise ValueError("Evaluator must report datasets")
    keys = set()
    for dataset, seeds in scores.items():
        if not re.fullmatch(r"[a-zA-Z0-9_-]+", dataset) or not isinstance(seeds, dict) or not seeds:
            raise ValueError("Evaluator must report per-seed scores")
        for seed, value in seeds.items():
            if not re.fullmatch(r"[0-9]+", seed) or type(value) not in (int, float) or not 0 <= value <= 1:
                raise ValueError("Expected finite accuracy values in [0, 1] keyed by seed")
            keys.add((dataset, seed))
    return keys


def render_table(report):
    baseline = report["test"]["run_0"]
    candidate = report["test"][report["selected_run"]]
    lines = [r"\begin{tabular}{lrrr}", r"\hline",
             r"Dataset & Baseline & Candidate & Delta (pp) \\", r"\hline"]
    for dataset, baseline_scores in baseline.items():
        a = mean(baseline_scores.values())
        b = mean(candidate[dataset].values())
        label = dataset.replace("_", r"\_")
        lines.append(f"{label} & {100*a:.2f} & {100*b:.2f} & {100*(b-a):+.2f} " + r"\\")
    lines.extend([r"\hline", r"\end{tabular}"])
    return "\n".join(lines) + "\n"


def current_report(folder, evaluator):
    try:
        report = json.loads((folder / REPORT).read_text())
        if report["schema"] == SCHEMA and report["inputs"] == inputs(folder, evaluator):
            test = report["test"]
            if score_keys(test["run_0"]) == score_keys(test[report["selected_run"]]):
                if (folder / TABLE).read_text() == render_table(report):
                    return report
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        pass
    return None


def receipt_for(folder, pdf):
    return {"benchmark_sha256": digest(folder / REPORT), "pdf_sha256": digest(pdf)}


def record_pdf(pdf, benchmark_hash):
    receipt = {"benchmark_sha256": benchmark_hash, "pdf_sha256": digest(pdf)}
    atomic_write(pdf.with_suffix(".benchmark.json"), json.dumps(receipt) + "\n")


def pdf_matches_report(folder, pdf):
    try:
        return json.loads(pdf.with_suffix(".benchmark.json").read_text()) == receipt_for(folder, pdf)
    except (OSError, ValueError):
        return False


def verify(folder, evaluator, timeout):
    with locked(str(folder / "runs")):
        cached = current_report(folder, evaluator)
        if cached:
            return cached
        original = inputs(folder, evaluator)
        validation = {run: score(evaluator, folder, run, "validation", timeout)
                      for run in original["checkpoint_sha256"]}
        reference_keys = score_keys(validation["run_0"])
        if any(score_keys(scores) != reference_keys for scores in validation.values()):
            raise ValueError("Validation datasets and seeds must match across runs")

        candidates = [run for run in validation if run != "run_0"]
        selected = max(candidates, key=lambda run: mean(
            mean(values.values()) for values in validation[run].values()
        ))
        test = {run: score(evaluator, folder, run, "test", timeout) for run in ("run_0", selected)}
        if any(score_keys(scores) != reference_keys for scores in test.values()):
            raise ValueError("Test datasets and seeds must match the validation protocol")
        if inputs(folder, evaluator) != original:
            raise ValueError("Benchmark inputs changed during verification. Retry verification.")

        deltas = {
            dataset: {seed: value - test["run_0"][dataset][seed] for seed, value in scores.items()}
            for dataset, scores in test[selected].items()
        }
        report = {"schema": SCHEMA, "selected_run": selected, "inputs": original,
                  "validation": validation, "test": test, "paired_test_deltas": deltas}
        atomic_write(folder / TABLE, render_table(report))
        atomic_write(folder / REPORT, json.dumps(report, indent=2) + "\n")
        return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("idea_dir", type=Path)
    parser.add_argument("--timeout", type=int, default=120, help="Seconds per evaluation")
    args = parser.parse_args()
    folder = args.idea_dir.resolve()
    evaluator = evaluator_for(folder)
    if evaluator is None:
        parser.error("The workspace template has no benchmark_evaluator.py")
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    try:
        print(json.dumps(verify(folder, evaluator, args.timeout), indent=2))
    except ValueError as error:
        parser.exit(1, f"Verification failed. {error}\n")


if __name__ == "__main__":
    main()
