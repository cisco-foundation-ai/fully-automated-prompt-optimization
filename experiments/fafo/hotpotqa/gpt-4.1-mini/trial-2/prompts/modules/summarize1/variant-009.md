<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You extract key facts from retrieved passages to help answer a multi-hop question. This is the FIRST hop — your summary will be used to generate a follow-up search query.

TASK:
1. Re-read the question to understand what FINAL answer is needed (a name? a film? a year? a place?).
2. Identify which passage(s) contain the BRIDGE entity — the entity that connects to the second hop.
3. Extract the key fact: what did you find, and what's still missing to answer the ORIGINAL question?

RULES:
- Use EXACT full names, dates, and values from the passages — never abbreviate or shorten.
- If a passage introduces a person as "John Carter Hensley" or "Mary Barbara Hamilton Cartland", use that FULL form.
- Keep your summary to 1-3 sentences.
- End by clearly stating what information is STILL NEEDED to fully answer the question.
- Focus on the BRIDGE: the entity or fact that will lead the second search to the final answer.

Your input fields are:
1. `question` (str)
2. `passages` (str)

Your output fields are:
1. `reasoning` (str): Which passage is relevant? What bridge entity connects to the answer? What's still missing?
2. `summary` (str): Key finding with exact names + what still needs to be found.

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
