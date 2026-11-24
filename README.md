# ai-scientist (Claude Code plugin)

A Claude Code port of [SakanaAI/AI-Scientist](https://github.com/SakanaAI/AI-Scientist).
Claude subagents replace the external LLM calls and the Aider code editor. Small Python scripts handle
the literature search, the experiment run harness, LaTeX checks and compilation, and review aggregation.

Pipeline: **ideas -> novelty check -> experiments -> LaTeX paper -> ensemble review -> (optional) improvement**.

## Install

```bash
claude plugin marketplace add ~/ai-scientist-plugin
claude plugin install ai-scientist@ai-scientist-local
```

Restart Claude Code after installing. Requirements: Python 3 with `numpy` and `matplotlib`,
and `pdflatex` + `bibtex` for papers (`sudo apt install texlive-latex-extra texlive-fonts-recommended texlive-bibtex-extra`).
`chktex` is optional. Set `S2_API_KEY` for reliable Semantic Scholar access; without it, searches fall back to OpenAlex.

## Commands

| Command | Stage |
|---|---|
| `/ai-scientist:scientist <template> [--num-ideas 3] [--max-ideas 3] [--improvement] ...` | full pipeline |
| `/ai-scientist:ideas <template> [--num-ideas N] [--check-novelty] [focus]` | 1. idea generation |
| `/ai-scientist:novelty <exp-dir>` | 2. novelty check (parallel, one agent per idea) |
| `/ai-scientist:experiment <exp-dir> <IdeaName>` | 3. experiments (run_1..run_5, notes, plots) |
| `/ai-scientist:writeup <idea-folder>` | 4. LaTeX paper + citations + PDF |
| `/ai-scientist:review <paper.pdf or idea-folder>` | 5. NeurIPS-style ensemble review (works on any PDF) |
| `/ai-scientist:new-template <dir> [source]` | wrap your own code as a template |

Quick start (bundled CPU template, seconds per run):

```
/ai-scientist:scientist optim_toy --num-ideas 2 --max-ideas 1
```

Results land in `./ai_scientist/<template>/` in the current directory.

## Components

- `agents/`: idea-generator, novelty-checker, experimenter, paper-writer, paper-reviewer
- `skills/ai-scientist/`: pipeline reference, schemas, prompts, write-up guide, review form
- `scripts/`: `init_workspace.py`, `ideas.py`, `s2_search.py`, `init_idea.py`, `run_experiment.py`, `run_plot.py`, `latex_build.py`, `aggregate_reviews.py`
- `templates/optim_toy/`: numpy MLP + SGD on moons/circles

## Differences from the original

- Claude (any model your session uses) instead of GPT/Claude API calls plus Aider; no API keys needed except optional `S2_API_KEY`.
- Novelty checks and review ensembles run as parallel subagents.
- Literature search falls back from Semantic Scholar to OpenAlex on rate limits.
- Review is done by Claude reading the PDF, not a hard-coded GPT-4o reviewer.
- Defaults are smaller (3 ideas, not 50).

## Verified benchmarks

New `optim_toy` workspaces independently rescore the final model checkpoints. The evaluator ranks
candidates using fixed validation data, then evaluates the selected candidate and SGD baseline on a
separate test split. The paper includes a generated comparison table. Run verification independently
with `python3 scripts/verify_benchmark.py <idea-folder>`, or let the full pipeline run it before
write-up. Resume reuses a current score and refreshes it when the evaluator or checkpoints change.

`benchmark_results.json` contains checkpoint and evaluator hashes, per-seed accuracy and paired
test differences. The evaluator and checkpoints remain locally accessible to generated code.
This benchmark supports reproducible scoring. A blind holdout requires a separate execution sandbox.
Existing workspaces keep their copied template. To try the benchmark with an older workspace, start a
fresh one using `--workspace ai_scientist_verified`.

## Resuming and handling research data

Run `/ai-scientist:scientist --resume` from the project where you started. If several runs are
pending, specify the template and original `--workspace`. The local SQLite research index keeps
the original options, next stage, selected ideas, and stage outcomes. It links each workspace to its
research activities while the workspace files hold the ideas, metrics, code snapshots, and papers.
The review planner reuses validated reviewer files for the same PDF. For workspaces created before
the index, use `/ai-scientist:scientist <template> --resume` with the original options once.

The database is `research.sqlite3` under `${CLAUDE_CONFIG_DIR:-~/.claude}/ai-scientist/`. Set
`AI_SCIENTIST_STATE_DIR` before starting Claude Code to change that directory. From a Bash command in the original
project, run `python3 "$CLAUDE_PLUGIN_ROOT/scripts/research_state.py" status` to list saved runs or
`history <exp-dir>` to see a workspace's activity history.

Claude Code calls the `StopFailure` hook on a rate-limit error and the `SessionStart` hook when a
session starts or resumes. The first marks the interruption. The second restores the checkpoint
summary into Claude's context. Run the resume command after your usage is restored. Claude Code's
documented hook events do not include a usage-reset notification, so the plugin waits for your next
session or prompt. The current in-memory step may be repeated from its most recent saved artifact.

Experiment and plot subprocesses receive a temporary home and a limited environment. Their raw output
is discarded to avoid copying sensitive values into logs. The subprocesses retain the current user's
filesystem and network access. Use an isolated runtime for generated code or confidential data.
Template copies exclude symlinks, Git metadata and common secret files. Keep proprietary details and
personal information out of literature queries, which are sent to the selected search provider.

License: Apache-2.0 (same as the original project, whose prompts and structure are adapted here).
