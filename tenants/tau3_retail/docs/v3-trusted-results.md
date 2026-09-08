<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

# FAFO v3 Luna — trusted-only prompt optimization

## Data asset

The `fafo-v3-luna-v1` pipeline used the same trusted split plan as the previous Tau asset (split-plan SHA-256 `f30b3a3aa4ff43ff4664259b9f83b1e4d0ed08af031b766f36f35518ab5ca265`).

| Item | Count |
|---|---:|
| Feedback traces | 37 |
| Unlabeled traces | 331 |
| Total episode rubrics | 368 |
| Trusted episode rubrics | 37 |
| Inferred episode rubrics | 331 |
| Held rubric outputs | 0 |
| Reusable training guidelines | 6 |
| Protected split-specific guidelines | 18 |
| Intent clusters retained as sampling metadata | 50 |

GPT-5.6 Luna generated the case-specific rubrics. Every episode was processed; every rubric was guideline-grounded. The asset is at `awaiting_review` because inferred cases were not approved or released as part of this trusted-only experiment.

Trusted split membership was fixed before optimization:

| Split | Cases |
|---|---:|
| Training | 20 |
| Validation | 9 |
| Test | 4 |
| Regression | 4 |

## Fixed optimization controls

- Agent: `gpt-4.1-2025-04-14`, temperature 0
- Judge: `gpt-5.5`
- Optimization target: agent prompt only
- Training batch: the same 20 trusted cases for every pass
- Pass threshold: 90, with zero critical violations required
- Plateau: three consecutive variants that neither exceed the best pass count nor improve the best critical-violation frontier
- Native Tau held-out tasks remained sealed during optimization and selection; T008 was run once only after the prompt was frozen

## Training loop

The baseline was not charged to the optimization budget. Each candidate cost 20 agent episode inferences.

| Prompt | Passes | Pass rate | Mean score | Critical violations |
|---|---:|---:|---:|---:|
| Baseline | 12/20 | 60% | 88.37 | 8 |
| T001 | 13/20 | 65% | 85.72 | 13 |
| T002 | 16/20 | 80% | 93.52 | 5 |
| T003 | 16/20 | 80% | 95.36 | 2 |
| T004 | 14/20 | 70% | 91.34 | 7 |
| T005 | 17/20 | 85% | 96.09 | 2 |
| T006 | 16/20 | 80% | 94.76 | 3 |
| T007 | 17/20 | 85% | 97.03 | 0 |
| T008 | 18/20 | 90% | 95.68 | 1 |
| T009 | 16/20 | 80% | 94.44 | 3 |
| T010 | 15/20 | 75% | 95.34 | 3 |
| T011 | 18/20 | 90% | 96.64 | 5 |

T008 established the highest training pass count. T007 established the zero-critical frontier. T009, T010, and T011 did not improve either frontier, so the loop stopped at plateau after 220 charged training inferences.

## Validation selection

The baseline and the three strongest training candidates were evaluated once on the untouched validation split.

| Prompt | Passes | Pass rate | Mean score | Critical violations |
|---|---:|---:|---:|---:|
| Baseline | 4/9 | 44.44% | 84.92 | 6 |
| T005 | 5/9 | 55.56% | 87.95 | 4 |
| T007 | 5/9 | 55.56% | 88.34 | 5 |
| T008 | 7/9 | 77.78% | 97.69 | 1 |

T008 was selected because it had the best validation pass count, mean score, and critical-violation result.

## Protected trusted gates

| Gate | Prompt | Passes | Pass rate | Mean score | Critical violations | Infrastructure failures |
|---|---|---:|---:|---:|---:|---:|
| Test | T008 | 1/4 | 25% | 62.72 | 9 | 0 |
| Regression | T008 | 2/4 | 50% | 76.85 | 1 | 0 after scorer retry |

The regression runner initially received one invalid judge response. That judge call was retried against the preserved Tau episode, adding no agent inference. The retry scored 86.5385 with no critical violations; the table reports the recomputed four-case aggregate.

## Native Tau final holdout

After T008 was frozen, it was evaluated once on the same 22 native Tau Retail held-out tasks, four fixed trial seeds, and fixed runtime controls as the baseline and prior trusted-only run.

| Native metric | Baseline B0 | Prior trusted V019 | FAFO v3 trusted T008 |
|---|---:|---:|---:|
| Passes | 63/88 | 71/88 | 71/88 |
| `pass^1` | 0.7159 | 0.8068 | 0.8068 |
| `pass^2` | 0.6136 | 0.6742 | 0.6970 |
| `pass^3` | 0.5455 | 0.5909 | 0.6136 |
| `pass^4` | 0.5000 | 0.5455 | 0.5455 |
| Database matches | 63/88 | 73/88 | 72/88 |
| Read actions matched | 229/236 | 233/236 | 231/236 |
| Write actions matched | 113/144 | 125/144 | 125/144 |
| Complete NL-assertion trajectories | 35/36 | 34/36 | 35/36 |

T008 gained eight passes and 0.0909 `pass^1` over B0. In the paired result, 56 trajectories passed both prompts, seven passed only B0, 15 passed only T008, and 10 failed both (`p = 0.1338`, exact two-sided McNemar). T008 tied V019 on total passes and `pass^4`, while improving `pass^2` and `pass^3` by 0.0227. Against V019, each prompt uniquely passed 11 trajectories (`p = 1.0`).

All 88 T008 trajectories completed with normal user-stop termination. The run had no missing rewards, duplicate identities, retries, or infrastructure failures. Native holdout outcomes were not used to revise T008.

## Interpretation

The optimization succeeded on training and validation but did not generalize to the four-case protected test split. Relative to validation baseline, T008 improved pass rate from 44.44% to 77.78% and reduced critical violations from 6 to 1. On test, however, three failures involved complex multi-part scope control, operation-order constraints, or superseded user choices. The test cases also averaged 10.75 applicable criteria, versus 6.45 on T008 training and 9.00 on validation.

The FAFO judge test and native Tau holdout give different pictures: T008 scored poorly on the four-case protected FAFO test but improved native Tau `pass^1` by 0.0909 over B0 and matched the prior trusted-only prompt's total native passes. This divergence is evidence that the four-case proxy gate is noisy and/or emphasizes requirements differently from native Tau scoring. Neither protected result should be used to revise the prompt in this experiment arm. A later, separately declared experiment can test whether inferred rubrics improve coverage before a fresh held-out evaluation.

## Inference ledger

| Purpose | Agent episode inferences |
|---|---:|
| Training baseline, uncharged | 20 |
| Eleven training candidates | 220 |
| Validation selection | 36 |
| Selected prompt on test and regression | 8 |
| Total executed | 284 |
