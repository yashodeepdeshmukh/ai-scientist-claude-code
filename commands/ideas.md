---
description: AI-Scientist stage 1 - generate new research ideas for a template (with reflection) into ai_scientist/<exp>/ideas.json, optionally followed by the novelty check.
argument-hint: <template-name-or-path> [--num-ideas 3] [--check-novelty] [--workspace ai_scientist] [focus text]
---

Arguments: `$ARGUMENTS`

Load the `ai-scientist` skill. Resolve scripts and set up the workspace:

```bash
SCRIPTS="${CLAUDE_PLUGIN_ROOT}/scripts"
python3 "$SCRIPTS/init_workspace.py" <template> --workspace <workspace>
```

Spawn one `ai-scientist:idea-generator` agent with SCRIPTS, EXP_DIR, NUM_IDEAS (default 3),
NUM_REFLECTIONS=3 and the focus text. With --check-novelty, then run the novelty stage exactly as
`/ai-scientist:novelty` describes. Finish by printing `python3 $SCRIPTS/ideas.py list EXP_DIR/ideas.json`.
