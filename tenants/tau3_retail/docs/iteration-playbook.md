<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

# Iteration Playbook

## Prerequisites

- Read the global `docs/processes/prompt-iteration-loop.md` and this tenant's
  `docs/recipe.md`.
- Verify the pinned Tau sibling runtime and fixed split.
- Finalize a FAFO asset and verify its trusted/inferred counts and holds.
- Complete the unchanged-prompt baseline on the exact training view.
- Set `OPENAI_API_KEY` without persisting it.

## Iteration Loop

1. Choose one declared arm: trusted-only, full mixed, or staged.
2. Evaluate the unchanged prompt on the arm's fixed training census.
3. Analyze only training failures, including criterion verdicts and complete
   tool-result evidence.
4. Clone the incumbent prompt into a new immutable candidate file.
5. Add one reusable instruction addressing the dominant supported failure
   pattern; do not copy case facts, identifiers, answers, or rubric wording.
6. Run the independent variant review.
7. Evaluate every case in the arm's fixed training view.
8. Record the license-header-stripped prompt-body hash, parent, hypothesis,
   counts, agent inferences, passes, critical violations, mean, decision, and plateau state in
   `iteration-memory.jsonl` and `change-log.md`.
9. At plateau, evaluate the declared candidate set on validation and freeze the
   winner before test, regression, or native holdout.

For staged optimization, finish or explicitly stop the inferred phase, copy its
winner unchanged to the trusted baseline, then begin a new plateau counter on
`train_trusted.jsonl`.

## Stop Criteria

- Plateau: three consecutive completed candidates improve neither the
  incumbent pass count nor the critical-violation frontier.
- Terminal ceiling: every case passes, mean score is 100, and critical
  violations are zero.
- Operational stop: explicit user direction, unrecoverable infrastructure
  failure, or a predeclared hard cap.
- One training agent inference is one fresh Tau episode for one case under one
  candidate prompt. Scorer-only retry does not consume another agent inference.

## Regression Prevention

- Freeze task IDs, group assignments, seeds, agent/user models, temperatures,
  policy, tools, chain, judge, rubric asset, threshold, and dataset membership.
- Select on validation; do not use test or regression details for prompt edits.
- Require the selected prompt to pass the trusted regression gate before native
  holdout evaluation.
- Compare baseline and candidate on the identical native task/seed matrix.
- Report paired results and uncertainty; do not overstate small differences.

## Lessons Logging

Use one JSON object per completed or interrupted candidate in
`docs/iteration-memory.jsonl`. Preserve rejected candidates and retries. The
human-readable `docs/change-log.md` should explain:

- what changed and why;
- which training evidence supported the change;
- exact evaluation metrics and inference accounting;
- why the candidate advanced or was rejected; and
- whether the arm stopped at plateau, ceiling, interruption, or user redirect.

Never log raw feedback, customer data, protected held-out content, provider
credentials, or full provider payloads.
