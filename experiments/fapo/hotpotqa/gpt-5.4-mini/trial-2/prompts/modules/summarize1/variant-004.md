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

INSTRUCTIONS:
This is the FIRST hop of a multi-hop question. Your summary will be used to (1) generate a follow-up search query and (2) eventually answer the question.

- Identify the BRIDGE ENTITY — the intermediate entity that connects the question to its answer.
- Extract all facts about this bridge entity from the passages: full name, dates, attributes, relationships.
- If the question asks about a comparison (X vs Y), extract the relevant attribute for BOTH entities if available.
- If the question contains a description that identifies an entity, state which entity it refers to based on the passages.
- Quote exact names, numbers, and dates from the passages. Do NOT paraphrase proper nouns.
- If the passages do not contain the needed information, state what IS available rather than just saying "not found."

User: [[ ## question ## ]]
${question}

[[ ## passages ## ]]
${steps.retrieve_hop1.output}

Respond with the corresponding output fields, starting with the field `[[ ## reasoning ## ]]`, then `[[ ## summary ## ]]`, and then ending with the marker for `[[ ## completed ## ]]`.
