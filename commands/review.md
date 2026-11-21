---
description: AI-Scientist stage 5 - NeurIPS-style ensemble review of a paper PDF (any paper, or an idea folder's PDF) with meta-review and averaged scores.
argument-hint: <paper.pdf | idea-folder> [--num-reviews 5] [--num-reflections 5]
---

Arguments: `$ARGUMENTS`

Load the `ai-scientist` skill. Resolve `SCRIPTS` as in `/ai-scientist:scientist` step 0.

PAPER: the PDF given, or `<idea-folder>/<Name>.pdf` (Name from idea.json).
OUT_DIR: the idea folder, or `<pdf dir>/<pdf stem>_review/` for a standalone PDF.

1. Spawn num-reviews (default 5) `ai-scientist:paper-reviewer` agents in one message, each with
   PAPER, OUT=`OUT_DIR/review_<k>.json`, NUM_REFLECTIONS, REVIEWER_ID k and a distinct PERSONA
   (soundness, novelty and related work, clarity, significance, reproducibility).
2. As area chair, read all reviews; write `OUT_DIR/meta_review.json` with Summary, Strengths,
   Weaknesses, Questions, Limitations.
3. `python3 $SCRIPTS/aggregate_reviews.py OUT_DIR/review_[0-9]*.json --meta OUT_DIR/meta_review.json --out OUT_DIR/review.json`
4. Write `OUT_DIR/review.md` (scores table, decision, strengths, weaknesses, questions).
   Show the user the scores table, the decision, and the top weaknesses.
