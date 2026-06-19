<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You are synthesizing information from two retrieval hops to answer a multi-hop question.

Your task: Combine the first-hop context with the second-hop passages to identify the final answer entity or fact. Preserve exact names, dates, and numbers from the passages — do not paraphrase entity names.

Your input fields are:
1. `question` (str): The question being answered
2. `context` (str): Summary from the first retrieval hop
3. `passages` (str): Retrieved passages from the second retrieval hop

Your output fields are:
1. `reasoning` (str): Connect information across both hops to identify the answer.
2. `summary` (str): A 1-3 sentence summary stating the final fact(s) needed to answer the question. Use exact entity names and values from the passages.

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
