# Paper write-up guide (adapted from AI-Scientist perform_writeup.py)

Edit only `latex/template.tex`, one section at a time, replacing the placeholder text.
Before each section, write a short plan (bullet points as `%` comments) of what goes there.

General rules, checked after every section:
- Only report results that appear in notes.txt / run_*/final_info.json. Never invent numbers.
- Only include figures that exist in the idea folder (check with `ls *.png`). Reference each figure once.
- Only cite keys that are in the `references.bib` filecontents block. Add new entries there first.
- No unenclosed math symbols, no LaTeX syntax errors, close every environment.
- No placeholder text left (`TITLE HERE`, `INTRO HERE`, ...).
- Be concise; avoid repetition across sections.

## Section order and tips

1. **Title**: specific, names the method and the finding.
2. **Abstract**: one paragraph, no breaks. What we try to do and why it is relevant; why it is hard;
   our contribution; how we verify it (experiments and results).
3. **Introduction**: longer version of the abstract; contributions as a bullet list; optional future work.
4. **Background**: academic ancestors needed to understand the method; a "Problem Setting" subsection
   with formalism and notation; highlight unusual assumptions.
5. **Method**: what we do and why, using the Background formalism.
6. **Experimental Setup**: dataset, metrics, important hyperparameters, implementation details.
   Do not imagine hardware details.
7. **Results**: all runs in notes.txt compared to baseline; hyperparameters; fairness; ablations;
   limitations. Use the figures with captions that describe them using notes.txt.
8. **Conclusions and Future Work**: brief recap; future work as potential academic offspring.
9. **Related Work** (written after citations are gathered): compare and contrast with the cited work;
   say why their method does or does not apply to our problem setting.

## Citation loop (up to 20 rounds)

Each round: identify the most important missing citation (claim, method, dataset, baseline);
search with `s2_search.py "<query>" --format json --limit 10`; pick zero or more relevant results;
paste each `bibtex` entry into the filecontents block (rename the key if it clashes);
cite it at the right place with `\citet` / `\citep`. Stop early when no important citation is missing.

## Refinement pass

1. Re-think the title.
2. For each section in order: re-read and fix redundancy, unsupported claims, missing figure
   references, wrong numbers, and anything the checklist above flags. Keep the length similar.
3. Run `latex_build.py <idea_dir>`; fix every issue and every LaTeX error; repeat up to 5 times.
