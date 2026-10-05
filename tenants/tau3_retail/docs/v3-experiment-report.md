<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

# FAFO Luna Experiment Report

## Purpose

This experiment tested whether a small set of manually reviewed Tau Retail episodes with trusted user feedback could be turned into reusable evaluation guidance, extended into case-specific rubrics for a much larger unlabeled trace set, and then used by FAFO to improve the Tau agent prompt.

The independent outcome measure was native Tau scoring on a sealed, group-disjoint held-out set. FAFO guideline-judge scores were used for prompt optimization and selection, not as the final effectiveness measure.

## 1. Build the FAFO evaluation asset

### Inputs

| Input | Episodes |
|---|---:|
| Traces with manually reviewed trusted feedback | 37 |
| Traces without feedback | 331 |
| Total | 368 |

Split membership was fixed before guideline extraction. Only the 20 trusted training episodes were used to create reusable training guidelines; trusted validation, test, and regression feedback remained protected.

### Simplified FAFO data pipeline

1. Normalize each complete Tau episode as one FAFO case, retaining user and assistant messages, tool calls, tool results, runtime information, and trusted feedback when present.
2. Correlate trusted feedback with the trace and tool evidence to identify recurring mistakes and extract evaluation guidelines.
3. Consolidate the trusted training evidence into six reusable guidelines.
4. For every trusted and unlabeled episode, make one GPT-5.6 Luna rubric-generation call with the full trace and all split-permitted guidelines. Luna selects any applicable guidance and writes case-specific criteria. If none applies, it infers criteria from the trace itself.
5. Retain 50 deterministic intent clusters only as metadata for future batching and analysis. Clusters do not decide correctness or guideline applicability.
6. Generate rubrics for all 368 episodes. Approve 315 inferred cases, retain all 37 trusted cases, and hold 16 inferred cases linked to protected regression groups.

No synthetic cases were generated. Embeddings used `text-embedding-3-small`; case-specific rubric generation used `gpt-5.6-luna`.

### Released splits

| Split | Trusted | Approved inferred | Total |
|---|---:|---:|---:|
| Train | 20 | 216 | 236 |
| Validation | 9 | 63 | 72 |
| Test | 4 | 36 | 40 |
| Regression | 4 | 0 | 4 |
| Triage hold | 0 | 16 | 16 |

The four published splits therefore contained 352 cases; the actual optimization training pool contained 236. The 16 held cases remained outside train, validation, test, and regression.

## 2. Fixed experiment controls

- Optimization target: prompt only.
- Tau agent and user simulator: `gpt-4.1-2025-04-14`, temperature `0.0`.
- Guideline judge during optimization: `gpt-5.5`.
- Fixed Tau Retail policy, tool implementation, task split, user simulator, and runtime configuration.
- Native final evaluation: the same 22 sealed Retail tasks and four seeds (`626729`, `373753`, `361454`, `1567`) for every prompt, producing 88 trajectories per prompt.
- Native held-out results were not used to author or select the prompts.

## 3. Prompt-optimization arms

### Trusted-only arm

Every candidate was evaluated on the same 20 trusted training cases. T008 was selected on validation, then evaluated on the protected test and regression gates.

| Result | Value |
|---|---:|
| Winning training score | 18/20 passes |
| Winning training mean | 95.68 |
| Winning training critical violations | 1 |
| Validation score | 7/9 passes |
| Validation mean | 97.69 |
| Validation critical violations | 1 |
| Charged candidate-training inferences | 220 |
| Total pre-native agent inferences, including baseline and gates | 284 |

The training loop stopped after T009–T011 failed to improve either the best pass count or the critical-violation frontier.

### Full mixed arm

Each pass used the full 236-case training set: 20 trusted and 216 approved inferred cases. M004 was the winner; M005–M007 were three consecutive plateau misses.

| Result | Value |
|---|---:|
| Winning full-training score | 192/236 passes |
| Winning full-training mean | 95.0459 |
| Winning full-training critical violations | 48 |
| Trusted tier within M004 | 15/20 passes |
| Inferred tier within M004 | 177/216 passes |
| Agent-training inferences, M000–M007 | 1,888 |

### Staged arm

The first stage optimized on all 216 inferred training cases. S015 was the best completed prompt with 184/216 passes, 39 critical violations, and a mean score of 95.3620. That stage was redirected during S016 rather than stopped by a confirmed plateau. The second stage started from S015 and optimized on all 20 trusted cases. T001 won with 19/20 passes, zero critical violations, and a mean score of 98.0538; T002–T004 then produced three plateau misses.

| Scope | Attempted agent episodes | Completed scoring operations |
|---|---:|---:|
| Inferred S000–S015 | 3,459 | 3,456 |
| Interrupted S016, excluded from selection | 131 | 128 |
| Trusted T000–T004 | 100 | 100 |
| Total | 3,690 | 3,684 |

The difference between attempts and completed scoring operations comes from three explicit S008 recovery retries and three S016 episodes that were active when the run was redirected.

## 4. Native Tau held-out result

| Native Tau metric | Baseline B0 | Trusted-only T008 | Mixed M004 | Staged T001 |
|---|---:|---:|---:|---:|
| Passes | 63/88 | 71/88 | **73/88** | 71/88 |
| `pass^1` | 0.7159 | 0.8068 | **0.8295** | 0.8068 |
| `pass^2` | 0.6136 | 0.6970 | **0.7348** | 0.7045 |
| `pass^3` | 0.5455 | 0.6136 | **0.6932** | 0.6364 |
| `pass^4` | 0.5000 | 0.5455 | **0.6818** | 0.5909 |
| Database matches | 63/88 | 72/88 | **73/88** | 71/88 |
| Read actions matched | 229/236 | **231/236** | **231/236** | **231/236** |
| Write actions matched | 113/144 | 125/144 | **126/144** | 125/144 |
| Individual NL assertions met | 59/60 | 59/60 | **60/60** | **60/60** |
| Complete NL-assertion trajectories | 35/36 | 35/36 | **36/36** | **36/36** |

All four result files contain 88 unique task/trial/seed identities, 88 normal user-stop terminations, no missing rewards, no abnormal terminations, and no explicit episode retries.

### Paired native comparisons

| Comparison | Left-only passes | Right-only passes | Pass delta | Exact two-sided McNemar p |
|---|---:|---:|---:|---:|
| T008 vs B0 | 15 | 7 | +8 T008 | 0.1338 |
| M004 vs T008 | 11 | 9 | +2 M004 | 0.8238 |
| M004 vs T001 | 9 | 7 | +2 M004 | 0.8036 |
| M004 vs B0 | 16 | 6 | +10 M004 | 0.0525 |
| T001 vs T008 | 7 | 7 | Tie | 1.0000 |
| T001 vs B0 | 16 | 8 | +8 T001 | 0.1516 |

## 5. Conclusion

All three FAFO optimization arms improved native Tau `pass^1` over B0 on this held-out matrix. The full mixed arm was the descriptive winner, gaining 10 passes over B0 and two over each of the other optimized prompts. It also had the strongest `pass^2`, `pass^3`, `pass^4`, database, write-action, and complete-NL results.

The staged arm produced the strongest trusted-set judge result, but this did not translate into a native advantage over trusted-only optimization. T001 tied T008 on total native passes and trailed M004 by two. This suggests that jointly exposing optimization to trusted and inferred cases was more useful here than optimizing the two sources sequentially.

The evidence is promising but not yet statistically conclusive. No pairwise exact McNemar comparison crossed 0.05; M004 versus B0 was closest at `p = 0.0525`. This experiment validates end-to-end feasibility and gives a positive effectiveness signal, but it does not by itself isolate every pipeline component or replace replication on additional task matrices.

## 6. Artifacts

- Evaluation asset: local-only `fafo-v3-luna-v1` workspace (regenerate with this recipe)
- Trusted-only record: [`v3-trusted-results.md`](v3-trusted-results.md)
- Mixed-arm record: [`v3-mixed-results.md`](v3-mixed-results.md)
- Staged-arm record: [`v3-staged-results.md`](v3-staged-results.md)
- Four-way native comparison: [`v3-native-holdout.md`](v3-native-holdout.md)

This report intentionally excludes task-level held-out conversations and failure details so the sealed native set is not used for further prompt development.
