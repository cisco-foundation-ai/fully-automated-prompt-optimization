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
4. Classify failures into prompt-addressable and structural-addressable clusters. Parameter-addressable failures may be called out separately when retrieval depth, model settings, or other config knobs are the likely cause. `summary["skill_addressable"]` mirrors `prompt_addressable` — prompt and skill are co-equal textual levels for the same reasoning/format failures; surface skill as an addressable level when the tenant has skill files (`tenants/<tenant_id>/skills/`) and `chain.config.optimization_target` includes `skill` or `both`.
5. Recommend the cheapest allowed level that can address the largest cluster. For textual clusters in skill-enabled tenants, note whether a reusable procedure (skill) or the base scaffold (prompt) is the better owner.

## Output

Return:

- `level_partition`: counts and clusters for prompt, skill (when the tenant is skill-enabled), parameter when applicable, and structural
- `recommended_level`
- `ceiling_estimate`
- `clusters`: label, count, representative case IDs, level (`prompt`/`skill`/`parameter`/`structural`), confidence, and suggested fix
