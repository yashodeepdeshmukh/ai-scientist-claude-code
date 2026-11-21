---
description: Create an AI-Scientist template from your own experiment code (experiment.py --out_dir contract, final_info.json, plot.py labels, prompt.json, seed ideas, LaTeX skeleton) and verify the baseline runs.
argument-hint: <new-template-dir> [source code path or description]
---

Arguments: `$ARGUMENTS`

Load the `ai-scientist` skill and read its "Template contract". Use the bundled
`${CLAUDE_PLUGIN_ROOT}/templates/optim_toy` as the reference implementation.

1. Understand the user's source code (or description): what is trained or simulated, the datasets,
   the metrics, the runtime of one run.
2. Create `<new-template-dir>/` with:
   - `experiment.py`: only `--out_dir`; writes `final_info.json` as `{dataset: {"means": {...}, "stds": {...}}}`
     and the per-run curves plot.py needs. One run should finish well under 2 hours; aim for minutes.
   - `plot.py`: `labels = {"run_0": "Baseline"}`; writes *.png to its working directory.
   - `prompt.json`: `system` and a `task_description` that explains the code, metrics, and what kind of
     ideas are in scope.
   - `seed_ideas.json`: 2 example ideas in the idea schema.
   - `latex/template.tex`: copy from optim_toy; replace the seed references with 2-4 core references
     for this domain (keep the filecontents[overwrite] block and graphicspath).
3. Verify: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/init_workspace.py" <new-template-dir> --workspace /tmp/ais_check`
   must print baseline means; fix until it does. Remove /tmp/ais_check afterwards.
4. Tell the user how to run it: `/ai-scientist:scientist <new-template-dir>`.
