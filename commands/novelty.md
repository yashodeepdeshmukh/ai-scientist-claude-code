---
description: AI-Scientist stage 2 - check unchecked ideas in ideas.json for novelty against Semantic Scholar / OpenAlex, one parallel agent per idea.
argument-hint: <exp-dir-or-template-name> [--all] [--idea Name] [--workspace ai_scientist]
---

Arguments: `$ARGUMENTS`

Load the `ai-scientist` skill. Resolve `SCRIPTS` as in `/ai-scientist:scientist` step 0.
EXP_DIR is the argument if it is a directory holding ideas.json, else `<workspace>/<template-name>`.

Ideas to check: `--idea Name` -> only that idea; `--all` -> every idea (re-check);
default -> `python3 $SCRIPTS/ideas.py list EXP_DIR/ideas.json --unchecked`, skipping status `seed`.

Spawn one `ai-scientist:novelty-checker` per idea in a single message (parallel). Pass SCRIPTS, EXP_DIR,
IDEA_NAME and the template task_description from `EXP_DIR/template/prompt.json`.
If S2_API_KEY is not set, mention once that Semantic Scholar may rate-limit and the search falls back to OpenAlex.
Finish by printing `python3 $SCRIPTS/ideas.py list EXP_DIR/ideas.json`.
