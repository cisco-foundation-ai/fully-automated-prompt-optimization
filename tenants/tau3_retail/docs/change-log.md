<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

# Change Log

## 2026-09-08 — Publishable Tau-3 FAFO V3 recipe

- Added a pinned, side-by-side Tau `v1.0.1` setup with an optional version-bound
  system-truststore patch.
- Added frozen Retail development/final-holdout membership, integrity hashes,
  baseline rollout commands, and a complete-episode FAFO exporter.
- Added outcome-blind feedback sampling, conversation-only review forms, and an
  explicit manual-trust join gate.
- Added the Tau episode chain, case-rubric judge, trusted/mixed/staged configs,
  exact V3 prompt lineages, experiment reports, and machine-readable iteration
  memory.
- Kept raw benchmark data, episodes, feedback, generated assets, evaluations,
  and credentials outside the published tenant.

## Recorded FAFO V3 evaluation asset

- Input: 37 manually reviewed trusted-feedback episodes plus 331 unlabeled
  episodes from 92 Tau Retail development tasks and four trials.
- Authoring: six reusable training guidelines, with error/success patterns
  extracted by correlating feedback with the full trajectory and tool evidence.
- Rubrics: one `gpt-5.6-luna` call per episode with all split-permitted
  guidelines; the model could select zero, one, or many applicable guidelines
  and infer trace-specific criteria when none applied.
- Controls: `text-embedding-3-small`, 50 clusters, rubric batch size 3,
  match-threshold compatibility setting 0.65, split seed 42, and synthetic
  coverage disabled.
- Output: 20 trusted + 216 inferred train, 9 + 63 validation, 4 + 36 test, four
  trusted regression cases, and 16 held inferred cases linked to regression
  groups. No synthetic cases were generated.
- Clustering: 50 all-user-message intent clusters retained only as sampling and
  analysis metadata.

## Recorded trusted-only arm

- Baseline: 12/20 passes, eight critical violations, mean 88.37.
- T008 was selected on validation after eleven 20-case candidates: 18/20 train,
  7/9 validation, and one validation critical violation.
- T009–T011 produced three plateau misses. Candidate training consumed 220
  agent inferences; all pre-native baseline, selection, and gates totaled 284.
- Exact prompts: `prompts/v3/trusted/`. Detailed results:
  [`v3-trusted-results.md`](v3-trusted-results.md).

## Recorded full-mixed arm

- Every candidate used the unchanged full 236-case training census.
- M004 won with 192/236 passes, 48 critical violations, and mean 95.0459 after
  adding lifecycle-first item-change routing.
- M005–M007 were three consecutive plateau misses. M000–M007 consumed 1,888
  agent inferences.
- Exact prompts: `prompts/v3/mixed/`. Detailed results:
  [`v3-mixed-results.md`](v3-mixed-results.md).

## Recorded staged arm

- Inferred stage: S015 won the completed candidates with 184/216 passes, 39
  critical violations, and mean 95.361966. S012 retained the 38-critical
  frontier. S016 was interrupted and excluded.
- Trusted stage: T001 added account-profile-versus-order-address separation and
  improved the inherited S015 prompt from 14/20 with 11 critical violations to
  19/20 with zero. T002–T004 then produced three plateau misses.
- Completed S000–S015 plus recovery attempts used 3,459 inferred-stage agent
  attempts; interrupted S016 attempted 131; T000–T004 used 100.
- Exact prompts: `prompts/v3/staged/`. Detailed results:
  [`v3-staged-results.md`](v3-staged-results.md).

## Recorded native Tau holdout

All prompts used the identical sealed 22-task × 4-trial matrix:

| Prompt | Passes | `pass^1` | `pass^2` | `pass^3` | `pass^4` |
|---|---:|---:|---:|---:|---:|
| Baseline B0 | 63/88 | 0.7159 | 0.6136 | 0.5455 | 0.5000 |
| Trusted T008 | 71/88 | 0.8068 | 0.6970 | 0.6136 | 0.5455 |
| Mixed M004 | **73/88** | **0.8295** | **0.7348** | **0.6932** | **0.6818** |
| Staged T001 | 71/88 | 0.8068 | 0.7045 | 0.6364 | 0.5909 |

M004 was the descriptive leader, but no exact paired McNemar comparison crossed
0.05. Native outcomes were not used for prompt creation or selection. See
[`v3-native-holdout.md`](v3-native-holdout.md).

## V3 lessons retained

- Full-episode tool results are essential; agent wording alone cannot establish
  mutation success.
- One case-specific rubric generation call is simpler than separate retrieval,
  deterministic-contract, and semantic-applicability gates.
- Intent clusters remain useful for split audits and batch sampling even when
  they do not choose guidelines.
- Joint trusted + inferred optimization was the strongest descriptive native
  arm in this run; staged optimization produced the strongest trusted judge
  score but not the strongest native score.
- Judge retries should reuse preserved episodes. Only fresh Tau episodes count
  as agent-training inferences.
- Small protected proxy splits can disagree with native evaluation; final claims
  should remain paired, native, and appropriately qualified.
