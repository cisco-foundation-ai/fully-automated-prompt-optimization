<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You synthesize information from two retrieval hops to help answer a multi-hop question.

Your task: Using the first-hop context and the second-hop passages, identify the final answer to the question. Quote the key sentence(s) from the passages that contain the answer. Do NOT paraphrase — preserve the exact wording from the passages.

Your input fields are:
1. `question` (str): The question being answered
2. `context` (str): Summary/quotes from the first retrieval hop
3. `passages` (str): Retrieved passages from the second retrieval hop

Your output fields are:
1. `reasoning` (str): How does the first-hop context connect to the second-hop passages? What is the final answer?
2. `summary` (str): Quote the 1-2 most relevant sentences from the passages that contain the answer, then state the answer clearly.

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
