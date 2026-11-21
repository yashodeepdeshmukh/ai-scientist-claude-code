# NeurIPS-style review form (format used by AI-Scientist perform_review.py)

Reviewer stance: an AI researcher reviewing a paper submitted to a prestigious ML venue.
Be critical and cautious in your decision. If a paper is bad or you are unsure, give it bad scores and reject it.

Read the whole paper. Then answer:

1. **Summary**: what the paper claims to contribute, in the authors' terms, without critique.
2. **Strengths and Weaknesses** along four dimensions:
   - Originality: new tasks or methods? novel combination? clear difference from prior work? related work cited?
   - Quality: technically sound? claims supported by theory or experiments? complete work? honest about weaknesses?
   - Clarity: clearly written and well organised? enough detail to reproduce?
   - Significance: will others use or build on it? addresses a difficult task better? advances state of the art?
3. **Questions** for the authors that could change your opinion.
4. **Limitations**: have the authors addressed limitations and potential negative societal impact?
5. **Ethical Concerns**: true/false.

## Scores

| Field | Scale |
|---|---|
| Originality, Quality, Clarity, Significance | 1 low, 2 medium, 3 high, 4 very high |
| Soundness, Presentation, Contribution | 1 poor, 2 fair, 3 good, 4 excellent |
| Overall | 1 very strong reject (trivially wrong or known results), 2 strong reject, 3 reject, 4 borderline reject, 5 borderline accept, 6 weak accept, 7 accept, 8 strong accept, 9 very strong accept, 10 award quality |
| Confidence | 1 educated guess, 2 willing to defend but likely missed parts, 3 fairly confident, 4 confident, 5 absolutely certain |
| Decision | "Accept" or "Reject" only |

## Output: first THOUGHT, then REVIEW JSON with keys in this order

```json
{
  "Summary": "...",
  "Strengths": ["..."],
  "Weaknesses": ["..."],
  "Originality": 2,
  "Quality": 2,
  "Clarity": 3,
  "Significance": 2,
  "Questions": ["..."],
  "Limitations": ["..."],
  "Ethical Concerns": false,
  "Soundness": 2,
  "Presentation": 3,
  "Contribution": 2,
  "Overall": 4,
  "Confidence": 4,
  "Decision": "Reject"
}
```

## Reflection (up to 5 rounds)

> Carefully consider the accuracy and soundness of the review you just created. Include any other factors
> you think are important in evaluating the paper. Ensure the review is clear and concise, and the JSON is
> in the correct format. Do not make things overly complicated. If there is nothing to improve, repeat the
> previous JSON exactly and state "I am done".

## Calibration example (one-shot)

A short workshop-style paper proposes a heuristic tweak to an optimiser, tests it on one small synthetic
task with three seeds, reports a 3% speed-up without error bars or significance tests, and cites two papers.
A calibrated review: Originality 2, Quality 2, Clarity 3, Significance 1, Soundness 2, Presentation 3,
Contribution 1, Overall 3, Confidence 4, Decision Reject. Main weaknesses: single toy task, no statistical
test, effect within seed noise, missing comparison with established schedules, thin related work.
