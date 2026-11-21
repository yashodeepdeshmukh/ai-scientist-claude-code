---
name: ai-scientist
description: Reference for the AI-Scientist research pipeline in Claude Code (idea generation, novelty check against Semantic Scholar/OpenAlex, automated experiment runs, LaTeX paper write-up, NeurIPS-style ensemble review). Use when running or resuming any /ai-scientist command, when working inside an ai_scientist/ workspace, when creating an AI-Scientist template, or when the user asks to auto-generate research ideas, run idea experiments, write up results as a paper, or review a paper PDF with NeurIPS scores.
---

# AI-Scientist for Claude Code

Port of SakanaAI's AI-Scientist (https://github.com/SakanaAI/AI-Scientist). Claude replaces the
external LLM calls and the Aider code editor. Python helper scripts replace the deterministic
plumbing (search API, run harness, LaTeX checks, review aggregation).

## Locate the scripts

Scripts live in `<plugin root>/scripts/`. This skill's base directory is `<plugin root>/skills/ai-scientist`,
so the scripts are at `../../scripts` relative to it. Commands pass the absolute path as `SCRIPTS=...`.
If neither is available:

```bash
SCRIPTS=$(dirname "$(find ~/.claude/plugins ~/ai-scientist-plugin -name s2_search.py -path '*scripts*' 2>/dev/null | head -1)")
```

## Pipeline (same order as launch_scientist.py)

| Stage | Who | Reads | Writes |
|---|---|---|---|
| 0. Workspace + baseline | `init_workspace.py` | template | `<exp>/template/run_0/final_info.json` |
| 1. Idea generation | `idea-generator` agent | prompt.json, experiment.py, seed_ideas.json, ideas.json | `<exp>/ideas.json` |
| 2. Novelty check | `novelty-checker` agent, one per idea | idea, `s2_search.py` | `novel`, `novelty_reason` per idea |
| 3. Experiments | `experimenter` agent, one per novel idea | idea folder | run_1..run_5, notes.txt, plot.py, figures |
| 4. Write-up | `paper-writer` agent | notes.txt, figures, latex/template.tex | `<Name>.pdf` |
| 5. Review | `paper-reviewer` agents (ensemble) + aggregation | PDF | `review.json`, `review.md` |
| 6. Improvement (optional) | `paper-writer` agent again | review.json | `<Name>_improved.pdf`, `review_improved.json` |

## Workspace layout (in the user's current directory)

```
ai_scientist/<exp>/
  template/                 copy of the template; template/run_0 = baseline
  ideas.json                all ideas, with novel / novelty_reason / status fields
  results/<YYYYmmdd_HHMMSS>_<Name>/
    idea.json notes.txt experiment.py plot.py
    run_0/ run_1/ ... run_5/  run_<i>.py snapshots  runs.jsonl
    *.png  latex/template.tex  <Name>.pdf
    review_*.json review.json review.md  log.md
```

Each idea `status` moves: `pending` -> `experiments_done` | `experiments_failed` -> `writeup_done` | `writeup_failed` -> `reviewed`.

## Template contract

A template directory must hold:
- `experiment.py` accepting only `--out_dir=<dir>`; writes `<dir>/final_info.json` as `{dataset: {"means": {metric: value}, ...}}`.
- `plot.py` with a `labels = {"run_i": "legend name"}` dict; writes `*.png` into its working directory.
- `prompt.json` with keys `system` and `task_description`.
- `seed_ideas.json`: list of idea objects (schema below).
- `latex/template.tex`: contains `\begin{filecontents}[overwrite]{references.bib} ... \end{filecontents}`
  and `\graphicspath{{../}{./}}` so figures in the idea folder resolve.

Bundled template: `optim_toy` (numpy MLP + SGD on synthetic data, CPU, seconds per run).
Use `/ai-scientist:new-template` to wrap your own code.

## Idea schema (ideas.json, identical to AI-Scientist)

```json
{"Name": "lowercase_with_underscores", "Title": "...", "Experiment": "implementation outline",
 "Interestingness": 1-10, "Feasibility": 1-10, "Novelty": 1-10,
 "novel": true, "novelty_reason": "...", "status": "pending"}
```

## Scripts

| Script | Purpose |
|---|---|
| `init_workspace.py <template> [--workspace DIR]` | copy template, run baseline run_0 + plot, print JSON paths |
| `ideas.py validate|list|set` | validate schema, list (`--novel-only`, `--unchecked`), set a field |
| `s2_search.py "query" [--limit 10] [--engine auto|semanticscholar|openalex] [--format text|json]` | literature search; JSON includes BibTeX |
| `init_idea.py <exp_dir> <Name>` | create the idea folder, seed notes.txt, print the folder path |
| `run_experiment.py <idea_dir> <n>` | run `experiment.py --out_dir=run_n` (n = 1..5), print means or stderr tail |
| `run_plot.py <idea_dir>` | run plot.py, list figures |
| `latex_build.py <idea_dir> [--check-only]` | cite/figure/duplicate checks, chktex, pdflatex+bibtex, copy PDF |
| `aggregate_reviews.py r1.json r2.json ... [--meta meta.json] [--out review.json]` | ensemble average |

## Limits copied from AI-Scientist

- Experiments: at most 5 runs (run_1..run_5), at most 4 consecutive failed attempts per run, timeout 7200 s per run.
- Novelty check: at most 10 search rounds per idea.
- Idea generation: 3 reflection rounds per idea by default.
- Write-up: citation loop of up to 20 rounds; one refinement pass per section; up to 5 LaTeX fix rounds.
- Review: ensemble of 5 reviewers by default, 5 reflection rounds each, 1 few-shot style example (from the form in `references/review_form.md`).

## Safety

The experimenter writes and executes code. Run inside a container, VM or throwaway WSL distro when possible,
and do not put credentials in the workspace. `run_experiment.py` enforces a timeout but no sandbox.

## References

- `references/idea_prompts.md`: idea generation and novelty-check instructions.
- `references/writeup_guide.md`: per-section tips and refinement checklist.
- `references/review_form.md`: NeurIPS-style review form, score scales and JSON format.
