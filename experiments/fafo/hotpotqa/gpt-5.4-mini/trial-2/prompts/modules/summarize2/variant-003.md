<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Your input fields are:
1. `question` (str):
2. `context` (str):
3. `passages` (str):
Your output fields are:
1. `reasoning` (str):
2. `summary` (str):
All interactions will be structured in the following way, with the appropriate values filled in.

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
In adhering to this structure, your objective is:
        Given the fields `question`, `context`, `passages`, produce the fields `summary`.

IMPORTANT INSTRUCTIONS:
- You have context from the first hop and new passages from the second hop.
- Combine ALL relevant facts from both sources that help answer the original question.
- Preserve exact names, dates, numbers, and relationships — do not paraphrase proper nouns.
- If the passages add missing information needed to complete the answer, highlight it clearly.
- Include specific entities and their attributes that relate to the question.
- Do NOT try to answer the question — only compile the relevant facts from both hops.
- Be concise but include all facts needed to determine the answer.

User: [[ ## question ## ]]
${question}

[[ ## context ## ]]
${steps.summarize_hop1.output}

[[ ## passages ## ]]
${steps.retrieve_hop2.output}

Respond with the corresponding output fields, starting with the field `[[ ## reasoning ## ]]`, then `[[ ## summary ## ]]`, and then ending with the marker for `[[ ## completed ## ]]`.
