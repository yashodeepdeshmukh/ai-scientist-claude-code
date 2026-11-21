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
test -f "$SCRIPTS/s2_search.py" || SCRIPTS=$(dirname "$(find ~/.claude/plugins ~/ai-scientist-plugin -name s2_search.py -path '*scripts*' 2>/dev/null | head -1)")
echo "$SCRIPTS"
command -v pdflatex bibtex || echo "WARNING: pdflatex/bibtex missing - write-up cannot compile (sudo apt install texlive-latex-extra texlive-fonts-recommended texlive-bibtex-extra)"
python3 "$SCRIPTS/init_workspace.py" <template> --workspace <workspace>
```

Keep `SCRIPTS`, `EXP_DIR`, and the baseline from the JSON output. Show the baseline to the user.
Append a dated entry for every stage to `EXP_DIR/log.md` (what ran, outcome).

## 1. Idea generation (skip with --skip-idea-generation)

Spawn one `ai-scientist:idea-generator` agent with SCRIPTS, EXP_DIR, NUM_IDEAS, NUM_REFLECTIONS=3, focus text.

## 2. Novelty check (skip with --skip-novelty-check)

List unchecked ideas: `python3 $SCRIPTS/ideas.py list EXP_DIR/ideas.json --unchecked`.
Skip seed ideas (status `seed`) unless no other ideas exist.
Spawn one `ai-scientist:novelty-checker` agent per idea, all in a single message so they run in parallel.
Include the template `task_description` in each prompt.
With --skip-novelty-check, set `novel` true for every pending idea.

## 3. Select ideas

Candidates: `novel == true` and status `pending`. Order by Interestingness + Feasibility + Novelty, descending.
Take the first max-ideas. If none are novel, report this and stop (suggest re-running with more ideas or
a focus). Show the selected list to the user.

## 4. Per idea: experiments, write-up, review

For each selected idea (sequentially; with --parallel, run the experimenter agents for all ideas in one message):

1. `IDEA_DIR=$(python3 $SCRIPTS/init_idea.py EXP_DIR <Name>)`
2. Spawn `ai-scientist:experimenter` with SCRIPTS, IDEA_DIR.
   Set status with `ideas.py set ... status '"experiments_done"'` or `'"experiments_failed"'`.
   Skip the next steps for a failed idea.
3. Spawn `ai-scientist:paper-writer` with SCRIPTS, IDEA_DIR. Set status `writeup_done` / `writeup_failed`.
4. Review ensemble: spawn num-reviews `ai-scientist:paper-reviewer` agents in one message, each with
   PAPER=`IDEA_DIR/<Name>.pdf`, OUT=`IDEA_DIR/review_<k>.json`, NUM_REFLECTIONS=5, REVIEWER_ID k, and
   different PERSONA values (soundness, novelty and related work, clarity, significance, reproducibility).
   Then act as area chair: read all reviews, write a meta-review JSON (`Summary`, `Strengths`,
   `Weaknesses`, `Questions`, `Limitations`) to `IDEA_DIR/meta_review.json`, and run
   `python3 $SCRIPTS/aggregate_reviews.py IDEA_DIR/review_[0-9]*.json --meta IDEA_DIR/meta_review.json --out IDEA_DIR/review.json`.
   Write a readable `IDEA_DIR/review.md`. Set status `reviewed`.
5. With --improvement: spawn `ai-scientist:paper-writer` with REVIEW=`IDEA_DIR/review.json`, then
   one `ai-scientist:paper-reviewer` with OUT=`IDEA_DIR/review_improved.json`.

## 5. Report

Print a table: idea, novel, runs completed, main result vs baseline, PDF path, Overall, Decision
(and improved Overall if run). Mention the workspace path and that every result can be resumed with the
single-stage commands (`/ai-scientist:experiment`, `/ai-scientist:writeup`, `/ai-scientist:review`).

Safety: experiments execute model-written code on this machine. Before stage 4 on a non-bundled template,
tell the user this in one line.
