<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

# FAFO staged optimization results

## Experiment

This arm optimized the Tau Retail prompt in two stages using the FAFO Luna evaluation assets:

1. Optimize on all 216 inferred training cases until the inferred-stage search was stopped.
2. Start from the best inferred-stage prompt and refine on all 20 trusted-feedback training cases until plateau.

Candidate ranking was lexicographic: more guideline passes, then fewer critical violations, then higher mean guideline score. The trusted stage declared plateau after three consecutive candidates improved neither the incumbent pass count nor the trusted critical-violation frontier. Validation, test, regression, and native Tau held-out tasks stayed sealed throughout optimization.

Fixed controls were `gpt-4.1-2025-04-14` for the agent and user simulator, temperature `0.0`, the fixed Retail policy and tools, and `gpt-5.5` for guideline judging.

## Stage 1: inferred cases

| Variant | Passes | Critical violations | Mean guideline score | Infrastructure failures |
|---|---:|---:|---:|---:|
| S000 baseline | 144/216 | 66 | 89.635178 | 0 |
| S001 | 161/216 | 43 | 92.496458 | 0 |
| S002 | 167/216 | 58 | 93.364081 | 0 |
| S003 | 175/216 | 48 | 94.798811 | 0 |
| S004 | 166/216 | 59 | 93.857166 | 0 |
| S005 | 168/216 | 56 | 93.980093 | 0 |
| S006 | 177/216 | 52 | 94.327677 | 0 |
| S007 | 179/216 | 47 | 94.418986 | 0 |
| S008, repaired | 174/216 | 51 | 94.788391 | 0 after 3 episode retries |
| S009 | 172/216 | 57 | 94.508849 | 0 |
| S010 | 180/216 | 46 | 95.093092 | 0 |
| S011 | 171/216 | 52 | 94.518213 | 0 |
| S012 | 176/216 | **38** | 95.301798 | 0 |
| S013 | 170/216 | 60 | 93.498330 | 0 |
| S014 | 167/216 | 59 | 93.259869 | 0 |
| **S015 inferred winner** | **184/216** | 39 | **95.361966** | 0 |

S015 won by the declared ranking because it had the most passes. S012 retained the inferred-stage critical frontier with 38 violations. S015 added explicit source-versus-target discipline for requests that copy a value between records.

S016 was interrupted when the experiment was redirected to the trusted stage. It had 128 completed cases and three active episode attempts at interruption, for 131 attempted agent episodes. It is incomplete, has no summary, and is excluded from candidate selection.

## Stage 2: trusted refinement

T000 is an exact prompt copy of S015 evaluated on the 20 trusted cases. T001 added one focused rule that separates account-profile addresses from each order shipping address. T002–T004 explored narrow formulations for the remaining relative-order-selection miss.

| Variant | Passes | Critical violations | Mean guideline score | Infrastructure failures | Frontier outcome |
|---|---:|---:|---:|---:|---|
| T000 inherited S015 | 14/20 | 11 | 92.146965 | 0 | Phase baseline |
| **T001 staged winner** | **19/20** | **0** | **98.053775** | 0 | New pass and critical frontier |
| T002 | 17/20 | 4 | 95.770510 | 0 | Miss 1 |
| T003 | 17/20 | 4 | 95.735110 | 0 | Miss 2 |
| T004 | 17/20 | 5 | 95.726315 | 0 | Miss 3; plateau |

The trusted stage stopped at the declared plateau. T001 is the final staged prompt. Relative to the inherited S015 prompt on trusted cases, it gained five passes, removed all 11 critical violations, and increased mean guideline score by 5.906810 points.

## Attempt and retry accounting

| Scope | Attempted agent episodes | Explicit episode retries | Completed scoring operations | Explicit scorer reruns |
|---|---:|---:|---:|---:|
| Inferred stage, S000–S015 | 3,459 | 3 | 3,456 | 0 |
| Interrupted S016 | 131 | 0 | 128 | 0 |
| Trusted stage, T000–T004 | 100 | 0 | 100 | 0 |
| **Total** | **3,690** | **3** | **3,684** | **0** |

The three explicit retries were the S008 recovery episodes. S016's three active episodes were interrupted, not retried. These counts are exact at the run/episode and completed-scoring-operation level. The OpenAI providers were configured with `max_retries: 2`, but transport-level retry attempts inside a successful provider call are not emitted into the evaluation artifacts; therefore no unsupported transport-retry count is claimed.

## Frozen T001 native Tau final holdout

After T001 was frozen and selected, it was run once on the same 22 native Tau Retail held-out tasks and four fixed trial seeds used by the earlier native evaluations. This evaluation used native Tau scoring only; it did not use the FAFO guideline judge and did not change the prompt.

| Native metric | T001 staged winner |
|---|---:|
| Reward / passes | 71/88 |
| Average reward / `pass^1` | 0.806818 |
| `pass^2` | 0.704545 |
| `pass^3` | 0.636364 |
| `pass^4` | 0.590909 |
| Database matches | 71/88 |
| Read actions matched | 231/236 |
| Write actions matched | 125/144 |
| Individual NL assertions met | 60/60 |
| Complete NL-assertion trajectories | 36/36 |
| Infrastructure failures | 0 |
| Normal user-stop terminations | 88/88 |
| Episode attempts | 88 |
| Episode retries | 0 |
| Hallucination retries | 0 |
| Resume events | 0 |

Trial pass counts were 17/22, 17/22, 20/22, and 17/22 for seeds 626729, 373753, 361454, and 1567 respectively. Across the 22 tasks, 13 passed all four trials, four passed three, three passed two, one passed one, and one passed none.

### Aggregate comparison on the identical native schedule

| Native metric | Baseline B0 | Mixed winner M004 | Staged winner T001 |
|---|---:|---:|---:|
| Reward / passes | 63/88 | **73/88** | 71/88 |
| Average reward / `pass^1` | 0.715909 | **0.829545** | 0.806818 |
| `pass^2` | 0.613636 | **0.734848** | 0.704545 |
| `pass^3` | 0.545455 | **0.693182** | 0.636364 |
| `pass^4` | 0.500000 | **0.681818** | 0.590909 |
| Database matches | 63/88 | **73/88** | 71/88 |
| Read actions matched | 229/236 | **231/236** | **231/236** |
| Write actions matched | 113/144 | **126/144** | 125/144 |
| Individual NL assertions met | 59/60 | **60/60** | **60/60** |
| Complete NL-assertion trajectories | 35/36 | **36/36** | **36/36** |

Against B0, T001 gained eight passes. The paired table was 55 both-pass, eight B0-only, 16 T001-only, and nine both-fail trajectories (`p = 0.1515896320`, exact two-sided McNemar).

Against M004, T001 had two fewer passes. The paired table was 64 both-pass, nine M004-only, seven T001-only, and eight both-fail trajectories (`p = 0.8036193848`, exact two-sided McNemar).

Agent cost was $6.661982 in total ($0.075704 per episode), user-simulator cost was $1.289232, and combined cost was $7.951214. The completed result contains all 88 unique task/trial/seed identities, no missing rewards, and exact task and seed coverage. The result SHA-256 is `7d23d13314b24200d03b4429d62392b00ebe4f2f8fa2044b6bbbdfbf563bcc7f`.

## Final artifact

The staged winner is [`prompts/v3/staged/trusted/t001.txt`](../prompts/v3/staged/trusted/t001.txt). No protected result was used to create or select it. Native Tau results and FAFO evaluation outputs remain local and are not published with this recipe.
