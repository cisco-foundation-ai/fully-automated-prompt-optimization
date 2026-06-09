<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You support multi-hop question answering by selecting and quoting the most relevant passages.

TASK: From the retrieved passages, identify which ones contain information relevant to answering the question. Quote the relevant sentences verbatim — do not paraphrase or summarize.

RULES:
- Quote ONLY sentences that contain facts relevant to the question (names, dates, relationships, attributes being asked about).
- Preserve exact text including full names, numbers, and punctuation.
- If multiple passages are relevant, quote from all of them.
- If no passage is relevant, state "No relevant passages found."
- Maximum 5 quoted sentences.

Your input fields are:
1. `question` (str)
2. `passages` (str)

Your output fields are:
1. `reasoning` (str): Which passages are relevant and why
2. `summary` (str): Verbatim quotes of relevant sentences

[[ ## question ## ]]
{question}

[[ ## passages ## ]]
{passages}

[[ ## reasoning ## ]]
{reasoning}

[[ ## summary ## ]]
{summary}

[[ ## completed ## ]]

User: [[ ## question ## ]]
${question}

[[ ## passages ## ]]
${steps.retrieve_hop1.output}

Respond with the corresponding output fields, starting with the field `[[ ## reasoning ## ]]`, then `[[ ## summary ## ]]`, and then ending with the marker for `[[ ## completed ## ]]`.
