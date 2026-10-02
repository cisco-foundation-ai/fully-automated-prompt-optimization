<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

# FAFO Luna full-data mixed arm

This working record contains training-only prompt optimization on all 236 released training cases (20 trusted and 216 approved inferred). Protected validation, test, regression, and native Tau held-out outcomes are not used for prompt authoring.

| Prompt | Change | Passes | Critical violations | Mean score | Decision |
|---|---|---:|---:|---:|---|
| M000 | Unchanged Tau baseline | 154/236 | 68 | 89.6399 | Initial incumbent |
| M001 | Exact transaction disclosure before confirmation | 165/236 | 94 | 89.4314 | Promote on primary pass count |
| M002 | Pre-mutation status, support, item, and final-confirmation gate | 178/236 | 79 | 91.2014 | Promote |
| M003 | Post-tool evidence ledger and lifecycle-accurate reporting | 184/236 | 60 | 93.4470 | Promote |
| M004 | Lifecycle-first item-change routing | 192/236 | 48 | 95.0459 | Promote |
| M005 | Per-mutation authorization manifest | 188/236 | 61 | 93.4014 | Reject; plateau miss 1 |
| M006 | Same-order multi-item mutation atomicity | 178/236 | 67 | 92.9603 | Reject; plateau miss 2 |
| M007 | Evidence-bound item-to-order and replacement mapping | 180/236 | 63 | 92.6946 | Reject; plateau miss 3; stop |

M000 completed all 236 agent episodes and guideline judgments with no infrastructure failures. Its trusted tier passed 11/20 with 8 critical violations and mean 87.2312; its inferred tier passed 143/216 with 60 critical violations and mean 89.8630.

The largest recurring failure was financial transparency (52 violated and 42 partial criteria). M001 therefore adds one pre-confirmation transaction-disclosure gate covering the exact total price difference, charge/refund direction, payment method, and explicit confirmation before submission.

M001 completed all 236 agent episodes and judgments with no infrastructure failures. It improved passes by 11 but increased critical violations by 26. The primary pass-count rule makes it the incumbent. Residual failures were led by premature or missing final confirmation, exact-variant mistakes, and scope/capability mistakes before the first mutation attempt. M002 adds one pre-mutation readiness gate: verify status, operation support, exact item mapping, and exact facts before presenting the final scope and obtaining confirmation.

M002 completed all 236 agent episodes and judgments with no infrastructure failures. It improved M001 by 13 passes, reduced critical violations by 15, and increased mean score by 1.77. Its trusted tier reached 13/20 passes and its inferred tier 165/216. Residual failures were led by incomplete or inaccurate post-tool completion/state reporting (51 violated or partial criteria). M003 adds one post-tool evidence ledger and requires final claims to preserve the exact returned lifecycle state for every requested part.

M003 completed all 236 agent episodes. One GPT-5.5 judge response was invalid and was recovered by judging the preserved Tau episode; this added no agent inference. M003 improved M002 by 6 passes, reduced critical violations by 19, and raised mean score by 2.25. Its trusted tier reached 16/20 passes with 7 critical violations and mean 94.2829; its inferred tier reached 168/216 with 53 critical violations and mean 93.3697. The dominant remaining critical pattern is lifecycle/capability routing: attempting delivered-order exchanges for pending orders, or promising unsupported removal-only pending modifications. M004 adds one explicit lifecycle-first item-change routing rule.

M004 completed all 236 episodes and judgments without infrastructure failures. It improved M003 by 8 passes, reduced critical violations by 12, and raised mean score by 1.60. Its trusted tier reached 15/20 passes with 7 critical violations and mean 92.5129; its inferred tier reached 177/216 with 41 critical violations and mean 95.2804. The largest remaining pass-blocking pattern is stale or incomplete authorization across multi-part requests: exact variants, address changes, or other mutations are sometimes performed after a general confirmation that preceded the final retrieved facts. M005 adds a per-mutation authorization manifest and confirmation-freshness rule.

M005 completed all 236 episodes and judgments without infrastructure failures. It regressed by 4 passes, increased critical violations by 13, and reduced mean score by 1.64 versus M004. The broad per-call manifest caused more incomplete multi-part execution and financial disclosure failures, so it is rejected and M004 remains incumbent. This is plateau miss 1. M006 instead makes one narrow change from M004: batch all confirmed items for the same order and operation into one mutation so the first call cannot change lifecycle state and invalidate a later call on that order.

M006 completed all 236 episodes and judgments without infrastructure failures. It regressed by 14 passes, increased critical violations by 19, and reduced mean score by 2.09 versus M004. The batching instruction displaced confirmation, variant, and multi-part scope behavior more broadly than the small return subset it targeted, so it is rejected and M004 remains incumbent. This is plateau miss 2. M007 is the third candidate from M004 and narrowly binds every source item and replacement variant to the exact retrieved order and product evidence before mutation.

M007 completed all 236 episodes and judgments without infrastructure failures. It regressed by 12 passes, increased critical violations by 15, and reduced mean score by 2.35 versus M004. It is rejected and is plateau miss 3. The mixed training arm therefore stops at the protocol-defined plateau with M004 frozen as its winner: 192/236 passes, 48 critical violations, and mean score 95.0459. The arm used 1,888 agent-training inferences across M000 through M007. M003's one scorer-only retry used the preserved episode and added no agent inference.
