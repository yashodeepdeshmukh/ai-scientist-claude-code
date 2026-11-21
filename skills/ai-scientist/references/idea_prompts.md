# Idea generation and novelty check

## Idea generation (per new idea)

Context to read first: `prompt.json` (system + task_description), the template `experiment.py`,
and every idea already in ideas.json (or seed_ideas.json if empty).

Instruction (adapted from AI-Scientist `idea_first_prompt`):

> Come up with the next impactful and creative idea for research experiments and directions you can
> feasibly investigate with the code provided. Note that you will not have access to any additional
> resources or datasets. Make sure any idea is not overfit to the specific training dataset or model,
> and has wider significance. The idea must differ from every previous idea.

First write THOUGHT: intuitions, motivation, high-level plan, and the ideal outcome of the experiment.
Then write the NEW IDEA as JSON with fields Name, Title, Experiment, Interestingness, Feasibility, Novelty.

Be cautious and realistic on ratings. Feasibility must reflect that the experiments run on the template's
hardware budget within the run timeout, with at most 5 runs, and that a single agent edits only
`experiment.py`/`plot.py`.

Reflection round (repeat up to NUM_REFLECTIONS = 3, stop early when satisfied):

> Carefully consider the quality, novelty, and feasibility of the idea you just created. Include any other
> factors you think are important. Ensure the idea is clear and concise, and the JSON is correct.
> Do not make things overly complicated. Try to keep the essence of the original idea unless there are
> glaring issues. If there is nothing to improve, repeat the previous JSON exactly and state "I am done".

## Novelty check (per idea, up to 10 rounds)

Role: an ambitious AI PhD student checking whether the idea is novel or not, i.e. whether it overlaps
significantly with existing literature or has already been well explored. Be a harsh critic for novelty.
A not-novel decision is justified if a paper sufficiently overlaps with the idea.

Each round:
1. THOUGHT about the idea and the results of the previous search (none in round 1).
2. Either decide, writing exactly `Decision made: novel.` or `Decision made: not novel.`,
   or run one new search: `python3 $SCRIPTS/s2_search.py "<query>" --limit 10`.

Do not decide novel in round 1; search at least twice with different phrasings
(method name, mechanism, target problem). If no decision after 10 rounds, the idea is NOT novel (default False).
Record the 1-3 most overlapping papers as the reason.
