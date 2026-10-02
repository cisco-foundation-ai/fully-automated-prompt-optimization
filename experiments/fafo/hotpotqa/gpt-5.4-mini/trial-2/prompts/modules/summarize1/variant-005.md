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
This is the FIRST hop of a two-hop question-answering pipeline.

Your goal: extract from the passages the KEY ENTITY or FACT needed to perform the second retrieval hop.

For multi-hop questions, the pattern is usually:
- The question describes entity A through some relationship → you need to identify entity A
- Then a second search will find the final answer about entity A

In your reasoning:
1. Parse what the question is asking and what intermediate entity is needed.
2. Search the passages for that entity, noting its EXACT full name as written.
3. Note any other relevant facts (dates, attributes) that may help answer the question.

In your summary:
- State the identified bridge entity with its FULL name exactly as it appears in the passages.
- Include key facts about it (birth date, occupation, location, etc.) that are relevant to the question.
- For comparison questions (X vs Y), extract the relevant attribute for EACH entity if present.
- If multiple candidate entities exist in the passages, list all of them with distinguishing facts.

User: [[ ## question ## ]]
${question}

[[ ## passages ## ]]
${steps.retrieve_hop1.output}

Respond with the corresponding output fields, starting with the field `[[ ## reasoning ## ]]`, then `[[ ## summary ## ]]`, and then ending with the marker for `[[ ## completed ## ]]`.
