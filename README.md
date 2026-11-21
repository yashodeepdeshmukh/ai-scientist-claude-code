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

## Safety

As with the original, the experiment stage executes model-written code. Prefer a container, VM or
throwaway WSL distro, and keep credentials out of the workspace.

License: Apache-2.0 (same as the original project, whose prompts and structure are adapted here).
