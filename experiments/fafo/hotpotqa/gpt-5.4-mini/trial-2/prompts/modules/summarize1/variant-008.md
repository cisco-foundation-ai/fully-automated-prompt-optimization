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

Your task:
1. Parse the question to understand what intermediate entity or fact is needed.
2. Search the passages for that entity/fact.
3. Extract it with EXACT names, dates, and attributes as written in the passages.

Key rules:
- Identify the BRIDGE ENTITY — the entity that connects the question to its answer. Use its FULL NAME exactly as it appears in the passages.
- If the question describes an entity indirectly (e.g., "the director of X"), identify which specific entity matches that description.
- For comparison questions (X vs Y), extract relevant attributes for BOTH entities.
- Include dates, birthplaces, occupations, and relationships that are relevant to the question.
- If the passages contain multiple candidates, state the MOST LIKELY one first but mention alternatives.
- Be concise: 2-4 sentences max. Focus only on facts needed to answer the question.
- Never say "not found" without also stating what WAS found that's potentially relevant.

User: [[ ## question ## ]]
${question}

[[ ## passages ## ]]
${steps.retrieve_hop1.output}

Respond with the corresponding output fields, starting with the field `[[ ## reasoning ## ]]`, then `[[ ## summary ## ]]`, and then ending with the marker for `[[ ## completed ## ]]`.
