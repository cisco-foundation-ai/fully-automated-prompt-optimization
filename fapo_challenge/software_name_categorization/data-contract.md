<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

# Data Contract

## Dataset Inventory

- `data/train.jsonl` - 80 cases, 10 per label.
- `data/eval.jsonl` - 40 cases, 5 per label.
- `data/test.jsonl` - 80 cases, 10 per label.
- Source: static checked-in JSONL files with real public software names.
- Label snapshot date: July 13, 2026.

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

The allowed labels are:

- `network_and_remote_access`
- `exposure_testing`
- `data_transfer_and_sync`
- `runtime_and_server_stack`
- `user_endpoint_clients`
- `sensitive_key_material`
- `security_posture_changes`
- `general_utility_other`

See `labels.md` for the label list.

## Check Expectations

- The model should output exactly one label string.
- The model input should be only the software name. Prompts should not require
  vendor, description, URL, or catalog fields.
- A FAPO scorer should perform case-insensitive exact match after stripping
  whitespace and common punctuation.
- Recommended `score_breakdown` keys:
  - `exact_match`: 0 or 100.
  - `valid_label`: 0 or 100.
- Recommended `composite_score`: `exact_match`.

## Dataset Handling

- Treat the checked-in JSONL files as the challenge source of truth.
- Validate that each split remains balanced across all labels after any dataset
  change.
- Verify real software names and category labels against public product pages
  or project documentation after any dataset change.
- Do not move these challenge JSONLs into `tenants/*/datasets/` as tracked files.
