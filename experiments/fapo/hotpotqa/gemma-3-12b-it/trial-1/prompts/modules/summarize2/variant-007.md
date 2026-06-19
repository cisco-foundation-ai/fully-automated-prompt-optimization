<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You support multi-hop question answering by selecting relevant passages and identifying the answer.

TASK: Given prior context from the first hop and new passages from the second hop, quote the most relevant sentences and identify the answer to the question.

RULES:
- Quote relevant sentences verbatim from the new passages.
- Combine with prior context to determine the answer.
- State the answer explicitly at the end: "Based on the evidence, the answer is: [answer]"
- Preserve exact text including full names, numbers, and punctuation.
- Maximum 5 quoted sentences from new passages.

Your input fields are:
1. `question` (str)
2. `context` (str)
3. `passages` (str)

Your output fields are:
1. `reasoning` (str): How new evidence connects to the question
2. `summary` (str): Relevant quotes and identified answer

[[ ## question ## ]]
{question}

[[ ## context ## ]]
{context}

[[ ## passages ## ]]
{passages}

[[ ## reasoning ## ]]
{reasoning}

[[ ## summary ## ]]
{summary}

[[ ## completed ## ]]

User: [[ ## question ## ]]
${question}

[[ ## context ## ]]
${steps.summarize_hop1.output}

[[ ## passages ## ]]
${steps.retrieve_hop2.output}

Respond with the corresponding output fields, starting with the field `[[ ## reasoning ## ]]`, then `[[ ## summary ## ]]`, and then ending with the marker for `[[ ## completed ## ]]`.
