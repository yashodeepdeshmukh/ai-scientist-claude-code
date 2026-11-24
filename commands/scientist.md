---
description: Run the full AI-Scientist pipeline on a template - generate ideas, check novelty, run experiments, write LaTeX papers, review them (optionally improve). Port of SakanaAI launch_scientist.py.
argument-hint: <template-name-or-path> [--num-ideas 3] [--max-ideas 3] [--skip-idea-generation] [--skip-novelty-check] [--improvement] [--num-reviews 5] [--resume] [--parallel] [--workspace ai_scientist] [focus text]
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

With --resume, skip stages 1–3. Run `python3 "$SCRIPTS/pipeline.py" EXP_DIR --num-reviews NUM_REVIEWS`
with --improvement if requested. Proceed to stage 4 for work items whose stage is other than
`complete`. Reuse the original --num-reviews value if supplied. If there are no working folders yet,
skip idea generation and continue at novelty checking with the saved ideas and the supplied flags.

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

## 4. Per idea

For a new selection, initialize every selected folder with
`python3 "$SCRIPTS/init_idea.py" EXP_DIR NAME --resume` before spawning any experimenters. For each
idea, call `python3 "$SCRIPTS/pipeline.py" EXP_DIR --idea NAME --num-reviews NUM_REVIEWS`. Pass
--improvement if requested. Use the plan's idea_dir and execute only the indicated stage.
Run ideas sequentially by default. With --parallel, experimenters for different ideas may run together.
After each successful stage, save the status immediately, then call the planner again. If a stage fails
or the next plan still reports the same stage, log its outcome and continue with the next idea.
Retry failed stages on the next --resume invocation.

- `experiments`: Spawn `ai-scientist:experimenter` with SCRIPTS and IDEA_DIR. Use
  `ideas.py set` to record status `experiments_done` or `experiments_failed`.
- `verify`: Run `python3 "$SCRIPTS/verify_benchmark.py" IDEA_DIR`. It ranks candidates using
  independently measured validation scores and then evaluates the selected candidate and baseline on
  the test split. Keep the finished runs if verification fails. Continue after verification succeeds.
- `writeup`: Spawn `ai-scientist:paper-writer` with SCRIPTS and IDEA_DIR. Record status `writeup_done`
  after a successful PDF build. Record `writeup_failed` on failure.
- `review`: Spawn `ai-scientist:paper-reviewer` only for reviewer slots with complete=false. Pass PDF
  and each slot's out path and id, NUM_REFLECTIONS=5, and a persona based on the ID (soundness,
  novelty and related work, clarity, significance, reproducibility, cycling if needed).
  Refresh the plan and defer aggregation if any review is missing or invalid.
  When every slot is complete, read all the reviews, write `IDEA_DIR/meta_review.json` (Summary,
  Strengths, Weaknesses, Questions, Limitations), and run
  `python3 "$SCRIPTS/aggregate_reviews.py" <all planned review paths> --meta IDEA_DIR/meta_review.json --out IDEA_DIR/review.json`.
  Write `IDEA_DIR/review.md` and record status `reviewed` after successful aggregation.
- `improvement`: Run `ai-scientist:paper-writer` with REVIEW=`IDEA_DIR/review.json`. Proceed after a
  successful build.
- `improved_review`: Review the planned improved PDF and save the review to the plan's out path.
- `complete`: Report the saved results.

## 5. Report

Print a table: idea, novel, runs completed, main result vs baseline, PDF path, Overall, Decision
(and improved Overall if run). Mention the workspace path and that every result can be resumed with the
single-stage commands (`/ai-scientist:experiment`, `/ai-scientist:writeup`, `/ai-scientist:review`).

Safety: experiments execute model-written code on this machine. Before stage 4 on a non-bundled template,
tell the user this in one line.
