<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

# Eval Config Schema

Evaluation configs use the **LangGraph chain** format. The chain is a compiled `StateGraph` built by a factory function in a tenant-defined Python module.

```json
{
  "tenant_id": "<tenant_id>",
  "provider": "<baseten|base10|sagemaker|openai>",
  "provider_settings": { "...": "..." },
  "dataset": {"path": "tenants/<tenant_id>/datasets/cases.jsonl"},
  "chain": {
    "path": "tenants/<tenant_id>/chains/<chain_module>.py",
    "fn": "build_chain",
    "config": {
      "prompt_paths": {
        "<step_name>": "tenants/<tenant_id>/prompts/variants/<variant>.md"
      }
    }
  },
  "scoring_profile": { "...": "..." },
  "output_dir": "tenants/<tenant_id>/evals/tmp/<run-name>"
}
```

### `dataset` fields

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `path` | string | yes | — | Literal repository-relative path to one JSONL dataset file |

The evaluation runtime does not resolve catalog pointers or directory aliases.
For an Evaluation Asset Studio release, use the exact immutable file path from
the asset manifest, for example
`tenants/<tenant_id>/datasets/evaluation_assets/<asset_id>/generations/sha256-<hash>/test.jsonl`.
`release.json` identifies the current generation for catalog readers, but it is
not itself a dataset and must not be used as `dataset.path`. Keeping the config
literal makes each evaluation run auditable against one immutable generation.

### `chain` fields

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `path` | string | yes | — | Path to the chain Python module (`.py` file) containing the factory function |
| `fn` | string | no | `"build_chain"` | Name of the factory function to call |
| `config` | object | no | `{}` | Arbitrary config dict passed to the factory function (e.g., prompt paths, parameters) |

The factory function signature must be:

```python
def build_chain(provider: ProviderClient, config: Dict[str, Any]) -> CompiledGraph
```

### `chain.config` conventions

`chain.config` is an arbitrary dict, but the engine and optimizer recognize a few conventional keys:

| Key | Type | Description |
|---|---|---|
| `prompt_paths` | object | Maps each chain step name to its prompt variant file |
| `skill_paths` | array | Skill files to load for an **agentic** tenant. Their bodies are injected at the agentic layer as a runtime `<available_skills>` context message (not inlined into the prompt). Omit for non-skill tenants. |
| `optimization_target` | string | `"prompt"`, `"skill"`, or `"both"` (default `"both"`). Selects which textual artifacts the optimizer iterates. `"skill"`/`"both"` with `skill_paths` set requires an `mcp` section (validated at config load). |

### Validation rules

- `chain` is required — configs without it raise `ValueError`
- `chain.path` must be non-empty
- every `chain.config.prompt_paths` / `chain.config.skill_paths` file must exist
- `optimization_target` must be one of `prompt` / `skill` / `both`; using `skill` / `both` with `skill_paths` requires a configured `mcp` server (skills are agentic-only)

## Provider Settings

`provider_settings` depends on the provider:

- `baseten` / `base10`: `base_url`, `model`, plus shared sampling/retry settings above.
- `sagemaker`: `api_url`, `api_key_env` (default `X_API_KEY`), plus shared sampling/retry settings above.
- `openai`: `model` (default `gpt-4o`), plus shared sampling/retry settings (`timeout_seconds`, `max_retries`, `retry_backoff_seconds`, `temperature`, `top_p`, `max_tokens`). Requires `OPENAI_API_KEY` environment variable.

## General Notes

Eval configs are ephemeral local files (for example, under
`tenants/<tenant_id>/configs/local-<run-name>.json`) and should not be committed.
A tracked starter template is available at
`docs/templates/eval-config.template.json`.

Storage operations use a separate tenant config at
`tenants/<tenant_id>/storage/config.json`, consumed by:

- `python -m hephaestus.cli customer-data pull ...`
- `python -m hephaestus.cli customer-data push ...` (use `--force` to overwrite existing GCS objects)
- `python -m hephaestus.cli customer-data remove-local --yes ...`

Notes:
- Core only requires `scoring_profile.scorer.module_path` (and optionally `class_name`).
- Other fields in `scoring_profile` are tenant-defined and interpreted by the tenant scorer.
