#!/usr/bin/env python3
"""Aggregate an ensemble of NeurIPS-style JSON reviews (AI-Scientist format).

Usage: aggregate_reviews.py review_1.json review_2.json ... [--out review.json]

Numeric fields are averaged and rounded (as AI-Scientist does after its meta-review);
Decision is the majority vote (ties -> Reject); list fields are merged without duplicates.
The text of the meta-review (Summary etc.) should be written by the meta-reviewer and
merged in with --meta meta.json, whose text fields override the merged ones.
"""
import argparse
import json
from collections import Counter

NUMERIC = {"Originality": (1, 4), "Quality": (1, 4), "Clarity": (1, 4), "Significance": (1, 4),
           "Soundness": (1, 4), "Presentation": (1, 4), "Contribution": (1, 4),
           "Overall": (1, 10), "Confidence": (1, 5)}
LISTS = ["Strengths", "Weaknesses", "Questions", "Limitations"]
ORDER = ["Summary", "Strengths", "Weaknesses", "Originality", "Quality", "Clarity", "Significance",
         "Questions", "Limitations", "Ethical Concerns", "Soundness", "Presentation", "Contribution",
         "Overall", "Confidence", "Decision"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("reviews", nargs="+")
    ap.add_argument("--meta", default=None)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    reviews = []
    for p in a.reviews:
        with open(p) as f:
            reviews.append(json.load(f))
    agg = {}
    for k, (lo, hi) in NUMERIC.items():
        vals = [r[k] for r in reviews if isinstance(r.get(k), (int, float)) and lo <= r[k] <= hi]
        if vals:
            agg[k] = int(round(sum(vals) / len(vals)))
    for k in LISTS:
        seen, merged = set(), []
        for r in reviews:
            for item in r.get(k, []) or []:
                if item not in seen:
                    seen.add(item)
                    merged.append(item)
        agg[k] = merged
    votes = Counter(r.get("Decision") for r in reviews if r.get("Decision") in ("Accept", "Reject"))
    agg["Decision"] = "Accept" if votes["Accept"] > votes["Reject"] else "Reject"
    agg["Summary"] = reviews[0].get("Summary", "")
    agg["Ethical Concerns"] = any(bool(r.get("Ethical Concerns")) for r in reviews)
    if a.meta:
        with open(a.meta) as f:
            meta = json.load(f)
        for k, v in meta.items():
            if k not in NUMERIC and k != "Decision":
                agg[k] = v
    agg["Ensemble"] = {"n": len(reviews), "Overall_scores": [r.get("Overall") for r in reviews],
                       "Decisions": [r.get("Decision") for r in reviews]}
    out = {k: agg[k] for k in ORDER if k in agg}
    out["Ensemble"] = agg["Ensemble"]
    text = json.dumps(out, indent=4)
    if a.out:
        with open(a.out, "w") as f:
            f.write(text)
    print(text)


if __name__ == "__main__":
    main()
