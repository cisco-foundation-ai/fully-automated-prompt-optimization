<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Your input fields are:
1. `question` (str):
2. `passages` (str):
Your output fields are:
1. `reasoning` (str):
2. `summary` (str):
All interactions will be structured in the following way, with the appropriate values filled in.

[[ ## question ## ]]
{question}

[[ ## passages ## ]]
{passages}

[[ ## reasoning ## ]]
{reasoning}

[[ ## summary ## ]]
{summary}

[[ ## completed ## ]]
In adhering to this structure, your objective is:
        Given the fields `question`, `passages`, produce the fields `summary`.

IMPORTANT INSTRUCTIONS:
- Extract ALL factual claims from the passages that could be relevant to answering the question.
- Include specific names, dates, numbers, and relationships exactly as stated in the passages.
- If multiple entities or facts are mentioned that could relate to the question, list ALL of them.
- Do NOT try to answer the question — only extract and organize the relevant facts.
- If the passages contain the bridge entity needed for a second search hop, make sure to include it with its full name.
- Keep your summary factual and concise. Do not speculate or infer beyond what the passages state.

User: [[ ## question ## ]]
${question}

[[ ## passages ## ]]
${steps.retrieve_hop1.output}

Respond with the corresponding output fields, starting with the field `[[ ## reasoning ## ]]`, then `[[ ## summary ## ]]`, and then ending with the marker for `[[ ## completed ## ]]`.
