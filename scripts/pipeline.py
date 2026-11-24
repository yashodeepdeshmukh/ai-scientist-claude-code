#!/usr/bin/env python3
"""Plan the next unfinished stage and identify reviews that can be reused."""
import argparse
import hashlib
import json
from pathlib import Path

from aggregate_reviews import LISTS, NUMERIC
from common import read_means
from ideas import load
from init_idea import find_idea_folder

EXPERIMENT_STATUSES = {"experiments_done", "writeup_failed", "writeup_done", "reviewed"}
PAPER_STATUSES = {"writeup_done", "reviewed"}


def read_review(path):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return None


def valid_review(path):
    review = read_review(path)
    return (
        isinstance(review, dict)
        and review.get("Decision") in ("Accept", "Reject")
        and isinstance(review.get("Summary"), str)
        and type(review.get("Ethical Concerns")) is bool
        and all(type(review.get(k)) is int and lo <= review[k] <= hi
                for k, (lo, hi) in NUMERIC.items())
        and all(isinstance(review.get(k), list) and all(isinstance(item, str) for item in review[k])
                for k in LISTS)
    )


def valid_aggregate(review):
    return (
        isinstance(review, dict)
        and type(review.get("Overall")) is int
        and 1 <= review["Overall"] <= 10
        and review.get("Decision") in ("Accept", "Reject")
    )


def review_slots(pdf, count):
    with pdf.open("rb") as paper:
        fingerprint = hashlib.sha256()
        for chunk in iter(lambda: paper.read(1048576), b""):
            fingerprint.update(chunk)
    directory = pdf.parent / "reviews" / fingerprint.hexdigest()
    directory.mkdir(parents=True, exist_ok=True)
    slots = []
    for number in range(1, count + 1):
        path = directory / f"review_{number}.json"
        slots.append({"id": number, "out": str(path), "complete": valid_review(path)})
    return slots


def has_experiment(folder):
    for run in folder.glob("run_[1-9]*"):
        if run.is_dir() and run.with_suffix(".py").is_file():
            try:
                read_means(run)
            except (OSError, ValueError):
                continue
            return True
    return False


def next_stage(idea, folder, num_reviews, improvement):
    work = {"name": idea["Name"], "idea_dir": str(folder)}
    status = idea.get("status")
    if status not in EXPERIMENT_STATUSES or not has_experiment(folder):
        return dict(work, stage="experiments")

    pdf = folder / f"{idea['Name']}.pdf"
    if status not in PAPER_STATUSES or not pdf.is_file() or not pdf.stat().st_size:
        return dict(work, stage="writeup")

    aggregate = read_review(folder / "review.json")
    if status != "reviewed" or not valid_aggregate(aggregate) or not (folder / "review.md").is_file():
        return dict(work, stage="review", pdf=str(pdf), reviewers=review_slots(pdf, num_reviews))

    if improvement:
        improved = folder / f"{idea['Name']}_improved.pdf"
        if not improved.is_file() or not improved.stat().st_size:
            return dict(work, stage="improvement")
        if not valid_review(folder / "review_improved.json"):
            return dict(work, stage="improved_review", pdf=str(improved))
    return dict(work, stage="complete")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("exp_dir", type=Path)
    parser.add_argument("--idea", help="Plan only this idea")
    parser.add_argument("--num-reviews", type=int, default=5)
    parser.add_argument("--improvement", action="store_true")
    args = parser.parse_args()
    if args.num_reviews < 1:
        parser.error("--num-reviews must be positive")

    exp_dir = args.exp_dir.resolve()
    plan = []
    for idea in load(exp_dir / "ideas.json"):
        if args.idea and idea["Name"] != args.idea:
            continue
        folder = find_idea_folder(exp_dir / "results", idea["Name"])
        if folder:
            plan.append(next_stage(idea, Path(folder), args.num_reviews, args.improvement))
    if args.idea and not plan:
        parser.error("No working folder for the requested idea")
    print(json.dumps(plan, indent=2))


if __name__ == "__main__":
    main()
