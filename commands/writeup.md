---
description: AI-Scientist stage 4 - write and compile the LaTeX paper for an idea folder from its notes.txt and figures (or revise it from a review with --review).
argument-hint: <idea-folder> [--cite-rounds 20] [--review path/to/review.json]
---

Arguments: `$ARGUMENTS`

Load the `ai-scientist` skill. Resolve `SCRIPTS` as in `/ai-scientist:scientist` step 0.
Check `command -v pdflatex bibtex`; if missing, tell the user the apt packages
(`texlive-latex-extra texlive-fonts-recommended texlive-bibtex-extra`) and still write the .tex.

Spawn one `ai-scientist:paper-writer` with SCRIPTS, IDEA_DIR, NUM_CITE_ROUNDS and REVIEW (if given).
Report the PDF path and any remaining issues from `latex_build.py`.
