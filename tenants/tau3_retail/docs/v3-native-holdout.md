<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

# FAFO v3 native Tau held-out comparison

## Outcome

The three frozen FAFO v3 winners were evaluated on the same 22 native Tau Retail held-out tasks and four fixed trial seeds (88 trajectories per prompt). Native outcomes were not used to create or select any prompt.

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

M004 was the descriptive leader at 73/88. Trusted-only T008 and staged T001 each reached 71/88, eight passes above B0. These are results from one fixed four-trial schedule, so small differences should not be treated as conclusive.

## Paired comparisons

| Comparison | Both pass | Left only | Right only | Both fail | Pass delta | Exact two-sided McNemar p |
|---|---:|---:|---:|---:|---:|---:|
| T008 vs B0 | 56 | 15 | 7 | 10 | +8 T008 | 0.1338 |
| M004 vs T008 | 62 | 11 | 9 | 6 | +2 M004 | 0.8238 |
| M004 vs T001 | 64 | 9 | 7 | 8 | +2 M004 | 0.8036 |
| M004 vs B0 | 57 | 16 | 6 | 9 | +10 M004 | 0.0525 |
| T001 vs T008 | 64 | 7 | 7 | 10 | Tie | 1.0000 |
| T001 vs B0 | 55 | 16 | 8 | 9 | +8 T001 | 0.1516 |

None of the pairwise differences meets a 0.05 threshold under the exact paired test. M004 versus B0 is the strongest signal (`p = 0.0525`) but remains just above that threshold.

## Trial and stability details

| Prompt | Trial 1 | Trial 2 | Trial 3 | Trial 4 | Tasks passing 4/4 | Recorded agent + user cost |
|---|---:|---:|---:|---:|---:|---:|
| B0 | 15/22 | 13/22 | 18/22 | 17/22 | 11/22 | $6.9293 |
| T008 | 19/22 | 19/22 | 16/22 | 17/22 | 12/22 | $7.1792 |
| M004 | 17/22 | 19/22 | 19/22 | 18/22 | **15/22** | $6.6908 |
| T001 | 17/22 | 17/22 | 20/22 | 17/22 | 13/22 | $7.9512 |

T008's task success distribution was one task at 0/4, one at 1/4, two at 2/4, six at 3/4, and 12 at 4/4. M004's distribution was two tasks at 1/4, four at 2/4, one at 3/4, and 15 at 4/4. T001's distribution was one task at 0/4, one at 1/4, three at 2/4, four at 3/4, and 13 at 4/4.

## Controls and integrity

- Tau release: `v1.0.1`, commit `fc0055dc4e0a316c3f83133267fbd6faaa770992`.
- Agent, user simulator, and native NL judge: `gpt-4.1-2025-04-14`; temperature `0.0`.
- Fixed Retail policy, tools, 22-task membership, four seeds (`626729`, `373753`, `361454`, `1567`), and concurrency of three.
- All four runs completed 88/88 trajectories with normal user-stop termination, zero missing rewards, zero duplicate task/trial/seed identities, zero abnormal terminations, and no explicit retries.
- T008 license-header-stripped prompt-body SHA-256: `7dfa48cf9c8857b02bb9fb3647b1d6d1d5fe86e1df7cbfe65a0b17ede104dafd`.
- M004 license-header-stripped prompt-body SHA-256: `492d414fc5b99a802cffb42deecb7de60bdc154abfd89a0707cecb2ceb293ca8`.
- T001 license-header-stripped prompt-body SHA-256: `1f84c4605f86f107942d1432613ce31a3f6208f74de99952341ddb3737aa6447`.
- B0 results SHA-256: `0a12af4d6a668664288315a06ac03a3c837339a729ff1d7bf097bdcf0a0e6d33`.
- T008 results SHA-256: `44cb8ff2d13c396760ea46d8d2f92dcb83667ac329cc0639bfe578cddace4172`.
- M004 results SHA-256: `12d7a6ccce5fbaaf136fd42b86017cf08b014479d6f62be0e355e76398486c13`.
- T001 results SHA-256: `7d23d13314b24200d03b4429d62392b00ebe4f2f8fa2044b6bbbdfbf563bcc7f`.

The aggregate results may be reported, but task-level held-out failures, conversations, and expected actions must not be used to revise or select prompts.
