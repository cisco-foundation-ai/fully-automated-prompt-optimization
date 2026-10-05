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
For an evaluation-asset release, use the exact immutable file path from
the asset manifest, for example
`tenants/<tenant_id>/datasets/evaluation_assets/<asset_id>/generations/sha256-<hash>/test.jsonl`.
The pipeline computes that literal path from the explicit repository/invocation base;
CLI and service entry points reject a tenants root outside that base before
creating or adopting an asset.
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
| `skill_paths` | array | Ordered skill files available to an **agentic** tenant. This setting does not itself inject a skill into a tenant chain: the factory must call `render_skills_block` and pass its result as `skills_text` to a node. That node injects one runtime `<available_skills>` message rather than inlining the body into the authored prompt. Omit for non-skill tenants. |
| `optimization_target` | string | `"prompt"`, `"skill"`, or `"both"` (default `"both"`). Selects which textual artifacts the optimizer iterates. `"skill"`/`"both"` with `skill_paths` set requires an `mcp` section when `run_evaluation` calls its path/preflight validation, not by `load_eval_config`. |

### Validation rules

- `chain` is required — configs without it raise `ValueError`
- `chain.path` must be non-empty
- every `chain.config.prompt_paths` / `chain.config.skill_paths` file must exist
- `optimization_target` must be one of `prompt` / `skill` / `both`; using `skill` / `both` with `skill_paths` requires a configured `mcp` server when `run_evaluation` calls its path/preflight validation (skills are agentic-only), not when `load_eval_config` parses the file

### `comparison.variant_dimensions`

`comparison.variant_dimensions`, when supplied, is an array without duplicates.
It may contain only these eight dimension names:

| Dimension | Meaning |
|---|---|
| `prompts` | Prompt-artifact identity may vary. |
| `skills` | Tenant-owned runtime skill artifacts may vary. |
| `chain_parameters` | Non-prompt/non-skill chain config may vary. |
| `chain_structure` | Chain factory and source identity may vary. |
| `provider` | Provider identity may vary. |
| `model` | Resolved model identity may vary. |
| `sampling` | Sampling settings may vary. |
| `mcp_capabilities` | Configured/discovered MCP capability identity may vary. |

`provider`, `model`, and `sampling` are independent dimensions: declaring a
model-only or sampling-only comparison does not require also declaring
`provider`. Each undeclared dimension remains a comparison control.

The ordered dataset membership, split membership, scorer, and metric are not
variant dimensions: dataset, split, scorer, and metric are permanent controls.
The run identity records the declared variation and fingerprints of those
controls for comparison auditability; it does not guarantee that a rerun
reproduces the same output.

## Provider Settings

`provider_settings` depends on the provider:

- `baseten` / `base10`: `base_url`, `model`, plus shared sampling/retry settings above.
- `sagemaker`: `api_url`, `api_key_env` (default `X_API_KEY`), plus shared sampling/retry settings above.
- `openai`: `model` (default `gpt-4o`), plus shared sampling/retry settings (`timeout_seconds`, `max_retries`, `retry_backoff_seconds`, `temperature`, `top_p`, `max_tokens`). Requires `OPENAI_API_KEY` environment variable.

### Tool-calling matrix

Tool support is determined by the provider implementation, not by an arbitrary
`provider_settings.supports_tools` flag. OpenAI non-reasoning models forward
tool schemas to the OpenAI client. `o1`, `o3`, `o4`, `gpt-5`, and `gpt5` are
text-only in the current implementation: a tool request falls back to normal
text generation. Baseten and SageMaker are text-only because they use the base
provider tool method, which also falls back to text generation.

### Persisted provenance limits

The safe run configuration records resolved provider/model/sampling facts and
fingerprints supported local inputs. It deliberately does not invent upstream
deployment facts. Its current provider facts set `provider_revision`,
`model_revision`, `api_revision`, `provider_request_id`, and
`provider_response_id` to `{"status": "unavailable"}`; its MCP facts likewise
set `implementation_revision` to `{"status": "unavailable"}`. Endpoint values
are fingerprinted rather than serialized. This audit record identifies the
local run configuration; it is not a remote-provider replay guarantee.

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
