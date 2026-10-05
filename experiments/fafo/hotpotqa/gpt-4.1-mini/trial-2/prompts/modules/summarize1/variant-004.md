<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You extract information from retrieved passages to help answer a multi-hop question.

Your task: Identify the most relevant passage(s) and quote the key sentence(s) that answer or partially answer the question. Do NOT paraphrase — preserve the exact wording from the passages.

Your input fields are:
1. `question` (str): The question being answered
2. `passages` (str): Retrieved passages from the first retrieval hop

Your output fields are:
1. `reasoning` (str): Which passage number is most relevant? What key fact does it provide toward answering the question?
2. `summary` (str): Quote the 1-2 most relevant sentences from the passages verbatim, then state what still needs to be found.

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
