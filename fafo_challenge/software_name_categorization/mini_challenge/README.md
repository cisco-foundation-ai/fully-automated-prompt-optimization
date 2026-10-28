<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

# Software Name Mini Challenge

A standalone manual prompt-tuning add-on for the software name categorization
challenge. It does not import FAFO code or tenant assets.

## Contents

| Level | Labels | Test subset (10 cases) | Starter prompt | Bundled FAFO v006 comparison |
|---|---|---|---|---|
| `easy` | 2 | `data/mini_test_easy.jsonl` | `prompts/starter_prompt_easy.txt` | `data/fafo_v006_results_easy.json` |
| `medium` | 4 | `data/mini_test_medium.jsonl` | `prompts/starter_prompt_medium.txt` | `data/fafo_v006_results_medium.json` |
| `difficult` | All 8 | `data/mini_test.jsonl` | `prompts/starter_prompt_difficult.txt` | `data/fafo_v006_results.json` |

Each test subset is fixed. Other files:

- `data/train_reference.jsonl`: the training dataset, as a ground-truth
  reference.
- `mini_eval.py`: a small evaluator that calls OpenAI directly.
- `server.py` and `web/`: a local UI for prompt editing, scoring, and
  comparison.

## Prerequisites

- Python 3.10 or newer.
- An OpenAI API key in `OPENAI_API_KEY`.
- Access to `gpt-4o-mini`.

## Run from the command line

```bash
cd fafo_challenge/software_name_categorization/mini_challenge
export OPENAI_API_KEY=<your-openai-api-key>
python3 mini_eval.py --level easy --prompt prompts/starter_prompt_easy.txt
```

The evaluator sends each software name to the selected model, normalizes the
returned label, and reports micro-F1. For this single-label exact-match task,
micro-F1 is the same as accuracy.

For other levels, pass `--level medium` or `--level difficult` with the
matching starter prompt from the table above.

Write a JSON result file:

```bash
python3 mini_eval.py \
  --level difficult \
  --prompt prompts/starter_prompt_difficult.txt \
  --output results/manual_results.json
```

Validate the bundled FAFO v006 comparison without calling OpenAI:

```bash
python3 mini_eval.py --level difficult --prompt prompts/starter_prompt_difficult.txt --fafo-reference
```

## Run the UI

```bash
cd fafo_challenge/software_name_categorization/mini_challenge
export OPENAI_API_KEY=<your-openai-api-key>
python3 server.py --host 127.0.0.1 --port 8766
```

Open `http://127.0.0.1:8766`.

The UI reads `OPENAI_API_KEY` from the server process environment. It shows the
training dataset as a ground-truth reference, lets participants edit a prompt,
runs the selected 10-case mini evaluation, and compares the manual result with
the bundled FAFO v006 reference for that level.
