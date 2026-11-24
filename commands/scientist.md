---
description: Run the full AI-Scientist pipeline on a template - generate ideas, check novelty, run experiments, write LaTeX papers, review them (optionally improve). Port of SakanaAI launch_scientist.py.
argument-hint: <template-name-or-path> [--num-ideas 3] [--max-ideas 3] [--skip-idea-generation] [--skip-novelty-check] [--improvement] [--num-reviews 5] [--parallel] [--workspace ai_scientist] [focus text]
---

# AI-Scientist: full pipeline

Arguments: `$ARGUMENTS`

Load the `ai-scientist` skill for layout, schemas and limits. Then run the stages below in order.
You are the orchestrator: delegate each stage to the named subagent with the Agent tool, pass absolute
paths, and keep only their summaries in context.

## 0. Setup

Parse the arguments. Defaults: num-ideas 3, max-ideas 3, num-reviews 5, workspace `ai_scientist`,
sequential experiments. Any text that is not a flag is a research focus for idea generation.

```bash
SCRIPTS="${CLAUDE_PLUGIN_ROOT}/scripts"
echo "$SCRIPTS"
command -v pdflatex bibtex || echo "WARNING: pdflatex/bibtex missing - write-up cannot compile (sudo apt install texlive-latex-extra texlive-fonts-recommended texlive-bibtex-extra)"
python3 "$SCRIPTS/init_workspace.py" <template> --workspace <workspace>
```

Keep `SCRIPTS`, `EXP_DIR`, and the baseline from the JSON output. Show the baseline to the user.
Append a dated entry for every stage to `EXP_DIR/log.md` (what ran, outcome).

## 1. Idea generation (skip with --skip-idea-generation)

Spawn one `ai-scientist:idea-generator` agent with SCRIPTS, EXP_DIR, NUM_IDEAS, NUM_REFLECTIONS=3, focus text.

## 2. Novelty check (skip with --skip-novelty-check)

List unchecked ideas with `python3 "$SCRIPTS/ideas.py" list EXP_DIR/ideas.json --unchecked`.
Check pending ideas. Include seed ideas when --skip-idea-generation is set.
Run one `ai-scientist:novelty-checker` per idea and pass the template's task description. Limit concurrent
checks to three to reduce rate limits. Leave failed or inconclusive checks eligible for a later retry.
When --skip-novelty-check is set, skip this stage and leave previous novelty verdicts unchanged.

## 3. Select ideas

Run `python3 "$SCRIPTS/ideas.py" select EXP_DIR/ideas.json --limit MAX_IDEAS`.
Pass `--include-seeds` for --skip-idea-generation and `--skip-novelty` for --skip-novelty-check.
Selection can include unchecked ideas only when explicitly requested. A recorded negative verdict still
excludes the idea. Report each selected idea's novelty verdict or unchecked status. If the selection
is empty, report the completed and inconclusive novelty checks and stop.

## 4. Per idea: experiments, write-up, review

For each selected idea (sequentially; with --parallel, run the experimenter agents for all ideas in one message):

1. `IDEA_DIR=$(python3 $SCRIPTS/init_idea.py EXP_DIR <Name> --resume)`
2. Spawn `ai-scientist:experimenter` with SCRIPTS, IDEA_DIR.
   Set status with `ideas.py set ... status '"experiments_done"'` or `'"experiments_failed"'`.
   Skip write-up and review when experiments fail.
3. Spawn `ai-scientist:paper-writer` with SCRIPTS and IDEA_DIR. Set `writeup_done` after a successful
   PDF build. If the build fails, set `writeup_failed` and skip review.
4. Create a fresh review directory under IDEA_DIR. Spawn num-reviews `ai-scientist:paper-reviewer`
   agents with PAPER=`IDEA_DIR/<Name>.pdf`, OUT=`REVIEW_DIR/review_<k>.json`, NUM_REFLECTIONS=5, REVIEWER_ID k, and
   different PERSONA values (soundness, novelty and related work, clarity, significance, reproducibility).
   Then act as area chair: read all reviews, write a meta-review JSON (`Summary`, `Strengths`,
   `Weaknesses`, `Questions`, `Limitations`) to `IDEA_DIR/meta_review.json`, and run
   `python3 "$SCRIPTS/aggregate_reviews.py" <current reviewer output paths> --meta IDEA_DIR/meta_review.json --out IDEA_DIR/review.json`.
   Aggregate the review files from this invocation only. Use the exact output paths sent to reviewers.
   Write `IDEA_DIR/review.md` and set status `reviewed` after successful aggregation.
5. With --improvement, spawn `ai-scientist:paper-writer` with REVIEW=`IDEA_DIR/review.json`. After a
   successful build, review PAPER=`IDEA_DIR/<Name>_improved.pdf` with OUT=`IDEA_DIR/review_improved.json`.

## 5. Report

Print a table: idea, novel, runs completed, main result vs baseline, PDF path, Overall, Decision
(and improved Overall if run). Mention the workspace path and that every result can be resumed with the
single-stage commands (`/ai-scientist:experiment`, `/ai-scientist:writeup`, `/ai-scientist:review`).

Safety: experiments execute model-written code on this machine. Before stage 4 on a non-bundled template,
tell the user this in one line.
