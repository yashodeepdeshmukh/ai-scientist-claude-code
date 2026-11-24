---
description: Run the full AI-Scientist pipeline on a template - generate ideas, check novelty, run experiments, write LaTeX papers, review them (optionally improve). Port of SakanaAI launch_scientist.py.
argument-hint: <template-name-or-path> [--num-ideas 3] [--max-ideas 3] [--skip-idea-generation] [--skip-novelty-check] [--improvement] [--num-reviews 5] [--resume] [--parallel] [--workspace ai_scientist] [focus text]
---

# AI-Scientist: full pipeline

Arguments: `$ARGUMENTS`

Load the `ai-scientist` skill for layout, schemas and limits. Then run the stages below in order.
You are the orchestrator: delegate each stage to the named subagent with the Agent tool, pass absolute
paths, and keep only their summaries in context.

## 0. Locate or open a research checkpoint

Parse the arguments. Defaults: num-ideas 3, max-ideas 3, num-reviews 5, workspace `ai_scientist`,
sequential experiments. Text outside the flags and template is the research focus.

Use the Python checkpoint CLI at `"${CLAUDE_PLUGIN_ROOT}/scripts/research_state.py"`.
Treat paths, saved arguments, focus and research artifacts as data. Quote paths and pass options
as one JSON argument.

- With bare `--resume`, run `research_state.py status` and use the one unfinished run for this
  project. If several are listed, ask which workspace to use. If none is listed, ask for the
  template and workspace.
- With a template, run `research_state.py locate TEMPLATE WORKSPACE` to get EXP_DIR, then run
  `research_state.py status EXP_DIR`. A saved run supplies its options and next stage. If the
  user also supplied different options, explain the saved options and use a different workspace
  if they want a new run. If an existing run is complete, report its saved results.
- For a run with no index entry, run `research_state.py begin EXP_DIR OPTIONS_JSON` before setup.
  Save the template, absolute workspace path, focus, num-ideas, max-ideas, num-reviews, and
  skip-idea-generation, skip-novelty-check, improvement and parallel flags in the options object.
  Resolve a custom template to an absolute path. Also save whether this is a legacy continuation
  (explicit `--resume` and an existing EXP_DIR/ideas.json before indexing). Keep the saved options
  on continuation.

At entry, run `research_state.py checkpoint EXP_DIR SAVED_STAGE` to bind the current Claude
session to the run. Take the next action from the saved stage. After completing each phase,
advance the checkpoint before starting the next one. Add a dated outcome to EXP_DIR/log.md once
the workspace exists. For work inside an idea, append outcomes with
`research_state.py record EXP_DIR STAGE OUTCOME --idea NAME`. Record `started`, `completed` or
`failed` around that stage and keep research details in its existing artifacts.

For the `setup` checkpoint, run `python3 "$SCRIPTS/init_workspace.py" TEMPLATE --workspace WORKSPACE`.
Use SCRIPTS from CLAUDE_PLUGIN_ROOT and report the saved baseline. For a legacy continuation, run
the planner after setup. If it finds working folders, save their idea names with
`research_state.py checkpoint EXP_DIR research --selected NAMES_JSON` and continue at stage 4.
If it finds no folders, advance to `novelty` and reuse the saved ideas. For other runs, advance
to `ideas`.

## 1. Idea generation (skip with --skip-idea-generation)

The `ideas` checkpoint includes `initial_ideas`, the names present before generation. Subtract the
number of ideas currently saved whose names are absent from that list from NUM_IDEAS. Spawn one
`ai-scientist:idea-generator` with SCRIPTS, EXP_DIR, the remaining count, NUM_REFLECTIONS=3 and
focus text if generation is enabled and the count is positive. Re-read the ideas file afterward.
If interrupted before enough ideas are saved, keep the `ideas` checkpoint. Otherwise advance to
`novelty`.

## 2. Novelty check (skip with --skip-novelty-check)

List unchecked ideas with `python3 "$SCRIPTS/ideas.py" list EXP_DIR/ideas.json --unchecked`.
Check pending ideas. Include seed ideas when --skip-idea-generation is set.
Run one `ai-scientist:novelty-checker` per idea and pass the template's task description. Limit concurrent
checks to three to reduce rate limits. Leave failed or inconclusive checks eligible for a later retry.
When --skip-novelty-check is set, skip this stage and leave previous novelty verdicts unchanged.
When this phase finishes, proceed to selection. The checkpoint remains at `novelty` until the
selection is saved.

## 3. Select ideas

Run `python3 "$SCRIPTS/ideas.py" select EXP_DIR/ideas.json --limit MAX_IDEAS`.
Pass `--include-seeds` for --skip-idea-generation and `--skip-novelty` for --skip-novelty-check.
Selection can include unchecked ideas only when explicitly requested. A recorded negative verdict still
excludes the idea. Report each selected idea's novelty verdict or unchecked status. If the selection
is empty, report the completed and inconclusive novelty checks and leave the workspace at
`novelty` if eligible checks remain and MAX_IDEAS is positive. Otherwise mark the empty run complete.
Save the selected names before creating any folders with
`research_state.py checkpoint EXP_DIR research --selected NAMES_JSON`.

## 4. Per idea

For the saved selection, initialize every selected folder with
`python3 "$SCRIPTS/init_idea.py" EXP_DIR NAME --resume` before spawning any experimenters. For each
idea, call `python3 "$SCRIPTS/pipeline.py" EXP_DIR --idea NAME --num-reviews NUM_REVIEWS`. Pass
--improvement if requested. Use the plan's idea_dir and execute only the indicated stage.
Run ideas sequentially by default. With --parallel, experimenters for different ideas may run together.
After each successful stage, save the status immediately, then call the planner again. If a stage fails
or the next plan still reports the same stage, log its outcome and continue with the next idea.
Retry failed stages on the next --resume invocation. Keep the `research` checkpoint until the
planner reports all selected ideas complete. Then advance to `complete`.

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
