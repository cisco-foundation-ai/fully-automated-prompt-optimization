<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

# FAFO Evaluation Asset Assistant for Codex

Use this phase when the user wants Codex to build, resume, check, or explain
an evaluation asset. The core code owns every data transformation and model
call. You write the build config, run the build, diagnose failures, check the
outputs, and walk the user through the review report.

Before operating, read `docs/references/data-pipeline.md` (steps, config,
outputs, case format) and `docs/processes/evaluation-input-contract.md`
(input format). `docs/processes/feedback-dataset-flow.md` explains the
concepts and trust model.

## Hard boundaries

- Do not implement pipeline steps yourself. Never label, split, redact, or
  write rubrics with ad hoc shell or Python; use `assets build`.
- Do not edit files inside an asset directory. A finished asset (one with
  `manifest.json`) is never rewritten; changes need a new `asset_id`.
- Do not change a started build's settings or inputs. The build refuses, and
  the fix is a new `asset_id`. Only `workers` can change on resume.
- Do not treat a recorded assistant response as ground truth.
- Do not silently substitute a model after a failure.
- Do not read tenant prompts, chains, or configs to make a build run. An asset
  can be a tenant's first artifact.
- Do not put tenant data, identifiers, or examples in shared repo locations.
  Treat `tenants/*/source_artifacts/` as protected.
- Show at most one bounded record when an example is needed.
- Do not add vendor field mappings to the core. Inputs must already follow
  `fafo-evaluation-input-v1`; a source adapter in tenant code produces them.
- Do not commit changes unless the user asks.

## Inputs to collect

- Tenant ID and asset ID.
- The labeled feedback JSONL (required, at least one record) and, optionally,
  the unlabeled JSONL, both in `fafo-evaluation-input-v1`.
- Settings that differ from the defaults: `model`, `split_seed`,
  `regression_split`, `observe_traces`, `redact`, `batch_size`,
  `min_lesson_confidence`, `min_guideline_support`, and `trace` filters.

## Workflow

1. Check that both inputs exist and read one record to confirm the contract.
   Do not rewrite them.
2. Write the config as `tenants/<tenant_id>/configs/<asset>.json`, which is
   git-ignored:

   ```json
   {
     "tenant_id": "<tenant_id>",
     "asset_id": "v1",
     "feedback": "tenants/<tenant_id>/source_artifacts/feedback.jsonl",
     "unlabeled": "tenants/<tenant_id>/source_artifacts/unlabeled.jsonl"
   }
   ```

3. Run the build. It needs `OPENAI_API_KEY`:

   ```bash
   python -m hephaestus.cli assets build --config tenants/<tenant_id>/configs/<asset>.json
   ```

4. If it fails, classify the cause before proposing a fix:
   - invalid input (the error names the file and line); fix the input and
     rerun, which is allowed because no asset was started;
   - credentials, model access, or a provider outage; rerun after fixing,
     and the response cache skips finished calls;
   - repeated invalid model output (`StepError`); report the step and the
     validation error;
   - a core defect.
5. When it finishes, check the outputs (below), then summarize `review.md`
   for the user.

## Checking an asset

- `manifest.json` exists, and its dataset counts match `review.json`.
- Every `datasets/<split>.jsonl` file loads, and each case has criteria in
  `expected.evaluation_guidelines`.
- Every lesson in `lessons.jsonl` comes from a train record in
  `splits.jsonl`. The build enforces this; report it if it ever fails.
- Excluded records and dropped lessons have reasons you can explain.

## Walking through the review report

Point the user to the parts of `review.md` that need judgment:

- weak or emerging guidelines, and guidelines whose criteria are too case
  specific to reuse;
- lessons set aside or marked `cannot_fix`;
- routes with no guideline, which yield only trace-inferred cases;
- rubrics with low confidence;
- model calls and token usage.

The report is the review step; there is no sign-off. If the user does not
trust the asset, the fix is a new build with different settings or inputs.

## Using the asset

Point an eval config's `dataset.path` at
`tenants/<tenant_id>/evaluation_assets/<asset_id>/datasets/<split>.jsonl`.
Train on `train`, select on `validation`, and test once on `test`. Score the
cases with a judge scorer that reads `expected.evaluation_guidelines`.

## OpenAI SSL troubleshooting

If the provider error reports SSL/TLS certificate verification:

1. Ask the user to run
   `python3 -m pip install --upgrade openai httpx certifi truststore`.
2. If the `truststore.inject_into_ssl()` blocks are commented out, uncomment
   them in `src/hephaestus/providers/openai.py` and
   `src/hephaestus/datasets/rubric_providers.py`.
3. Rerun the build; cached calls are reused.

Do not use this for invalid credentials, unavailable models, rate limits, or
malformed output.

## Report

- Tenant ID, asset ID, and asset path.
- Cases per split and trust tier, and excluded records with reasons.
- Guideline count by strength, and lessons kept, dropped, and set aside.
- Model, calls, and tokens.
- Anything in the review report the user should decide on.
