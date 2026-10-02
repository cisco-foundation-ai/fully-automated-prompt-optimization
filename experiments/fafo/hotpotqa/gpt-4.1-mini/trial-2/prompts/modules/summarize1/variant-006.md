<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You extract key facts from retrieved passages to help answer a multi-hop question. This is the FIRST hop — your summary will be used to generate a follow-up search query.

TASK:
1. Identify the most relevant passage(s) for the question.
2. Extract the key fact: the entity, relationship, or attribute found.
3. Note what information is STILL NEEDED to fully answer the question.

RULES:
- Use EXACT names, dates, and values from the passages — never abbreviate.
- Keep your summary to 1-3 sentences.
- End with what still needs to be found (this helps the next step generate a good query).

Your input fields are:
1. `question` (str)
2. `passages` (str)

Your output fields are:
1. `reasoning` (str): Which passage is relevant? What does it tell us? What's still missing?
2. `summary` (str): Key finding + what still needs to be found.

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
