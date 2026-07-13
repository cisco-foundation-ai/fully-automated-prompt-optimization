<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

# Software Name Mini Challenge

This is a standalone manual prompt-tuning add-on for the software name
categorization challenge. It does not import FAPO code or tenant assets.

The mini challenge contains:

- `data/train_reference.jsonl` - the training dataset as ground truth reference.
- `data/mini_test_easy.jsonl` - a fixed 10-case subset using 2 labels.
- `data/mini_test_medium.jsonl` - a fixed 10-case subset using 4 labels.
- `data/mini_test.jsonl` - a fixed 10-case difficult subset using all 8 labels.
- `data/fapo_v006_results_easy.json` - bundled FAPO v006 comparison for easy.
- `data/fapo_v006_results_medium.json` - bundled FAPO v006 comparison for medium.
- `data/fapo_v006_results.json` - bundled FAPO v006 comparison for difficult.
- `mini_eval.py` - a small evaluator that calls OpenAI directly.
- `server.py` and `web/` - a local UI for prompt editing, scoring, and comparison.

## Levels

- Easy: 2 labels.
- Medium: 4 labels.
- Difficult: 8 labels.

## Prerequisites

- Python 3.10 or newer.
- An OpenAI API key in `OPENAI_API_KEY`.
- Access to `gpt-4o-mini`.

## Run From The Command Line

```bash
cd fapo_challenge/software_name_categorization/mini_challenge
export OPENAI_API_KEY=<your-openai-api-key>
python3 mini_eval.py --level easy --prompt prompts/starter_prompt_easy.txt
```

The evaluator sends each software name to the selected model, normalizes the
returned label, and reports micro-F1. For this single-label exact-match task,
micro-F1 is the same as accuracy.

Use `--level medium` with `prompts/starter_prompt_medium.txt`, or
`--level difficult` with `prompts/starter_prompt_difficult.txt`.

To write a JSON result file:

```bash
python3 mini_eval.py \
  --level difficult \
  --prompt prompts/starter_prompt_difficult.txt \
  --output results/manual_results.json
```

To validate the bundled FAPO v006 comparison without calling OpenAI:

```bash
python3 mini_eval.py --level difficult --prompt prompts/starter_prompt_difficult.txt --fapo-reference
```

## Run The UI

```bash
cd fapo_challenge/software_name_categorization/mini_challenge
export OPENAI_API_KEY=<your-openai-api-key>
python3 server.py --host 127.0.0.1 --port 8766
```

Open `http://127.0.0.1:8766`.

The UI reads `OPENAI_API_KEY` from the server process environment. It shows the
training dataset as ground truth reference, lets participants edit a prompt,
runs the selected 10-case mini evaluation, and compares the manual result to the
bundled FAPO v006 reference for that level.
