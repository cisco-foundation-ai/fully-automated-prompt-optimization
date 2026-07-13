<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

# Data Contract

## Dataset Inventory

- `datasets/datasets/train.jsonl` - 80 cases, 10 per label.
- `datasets/datasets/eval.jsonl` - 40 cases, 5 per label.
- `datasets/datasets/test.jsonl` - 80 cases, 10 per label.

Copy these files from `fapo_challenge/software_name_categorization/data/` before
running this tenant locally. The copied tenant dataset files are runtime
artifacts and should not be tracked by git.

## Case Schema

```json
{
  "case_id": "swc_train_001",
  "task_type": "software_name_categorization",
  "context": {
    "software_name": "<real public software name>"
  },
  "expected": {
    "category": "<one allowed label>"
  },
  "metadata": {
    "split": "train | eval | test",
    "difficulty": "easy | medium | hard",
    "ambiguity_type": "<difficulty source>",
    "challenge": "software_name_categorization",
    "challenge_version": "v1",
    "source_type": "real_public_software_name",
    "snapshot_date": "2026-07-13"
  }
}
```

## Label Taxonomy

Allowed labels:

- `network_and_remote_access`
- `exposure_testing`
- `data_transfer_and_sync`
- `runtime_and_server_stack`
- `user_endpoint_clients`
- `sensitive_key_material`
- `security_posture_changes`
- `general_utility_other`

## Check Expectations

- The model should output exactly one label string.
- Matching is case-insensitive after stripping common punctuation and code fence
  markers.
- The scorer extracts the last non-empty output line as the candidate label.
- `composite_score` is exact-match correctness.
- `score_breakdown.f1` is exact-match correctness for each single-label case.
- `score_breakdown.valid_label` indicates whether the parsed output is an
  allowed label.
- `score_breakdown.strict_format` indicates whether the entire response was only
  the parsed label.

## Dataset Update Procedure

- Treat the challenge JSONLs under `fapo_challenge/` as the source of truth.
- If the challenge data changes, recopy the JSONLs into this tenant locally.
- Validate that each split remains balanced across all labels after any dataset
  change.
- Do not track copied dataset payloads under `tenants/*/datasets/`.

