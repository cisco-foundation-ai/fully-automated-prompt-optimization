<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

# FAPO Step Attribution Phase for Codex

Use this as an internal phase of the optimization workflow after each eval run.

## Inputs

- `eval_results_path`: path to `results.jsonl`
- `eval_config_path`: eval config JSON
- `tenant_id`: tenant being optimized

## Procedure

1. Read the results JSONL, eval config, chain code, scorer code, prompt files, and a small dataset sample.
2. Run the rule-based helper:

```python
from pathlib import Path
from src.hephaestus.analysis.step_attribution import attribute_failures, summarize

attribution = attribute_failures(Path(eval_results_path))
summary = summarize(attribution)
```

3. For low-confidence cases, inspect the actual step outputs and scorer requirements.
4. Classify failures into prompt-addressable and structural-addressable clusters. Parameter-addressable failures may be called out separately when retrieval depth, model settings, or other config knobs are the likely cause.
5. Recommend the cheapest allowed level that can address the largest cluster.

## Output

Return:

- `level_partition`: counts and clusters for prompt, parameter when applicable, and structural
- `recommended_level`
- `ceiling_estimate`
- `clusters`: label, count, representative case IDs, level, confidence, and suggested fix
