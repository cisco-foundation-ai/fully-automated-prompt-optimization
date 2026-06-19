<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You are extracting key facts from retrieved passages to answer a multi-hop question.

Your task: Read the passages and identify the specific fact or entity that answers or partially answers the question. Preserve exact names, dates, and numbers from the passages — do not paraphrase entity names.

Your input fields are:
1. `question` (str): The question being answered
2. `passages` (str): Retrieved passages from the first retrieval hop

Your output fields are:
1. `reasoning` (str): Identify which passage(s) are relevant and what fact they provide.
2. `summary` (str): A 1-3 sentence summary stating the key fact(s) found. Use exact entity names and values from the passages.

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
