---
description: AI-Scientist stage 3 - implement and run the experiments for one idea (run_1..run_5, notes.txt, plots).
argument-hint: <exp-dir> <IdeaName> | <idea-folder> [--max-runs 5]
---

Arguments: `$ARGUMENTS`

Load the `ai-scientist` skill. Resolve `SCRIPTS` as in `/ai-scientist:scientist` step 0.

- Given `<exp-dir> <IdeaName>`: `IDEA_DIR=$(python3 $SCRIPTS/init_idea.py <exp-dir> <IdeaName>)`.
- Given an existing idea folder (has idea.json): resume there; tell the experimenter which run_n exist already.

Warn in one line that the experiment executes model-written code locally.
Spawn one `ai-scientist:experimenter` with SCRIPTS, IDEA_DIR, MAX_RUNS. Then update the idea status in
`<exp-dir>/ideas.json` with `ideas.py set` and report the summary and figure list.
