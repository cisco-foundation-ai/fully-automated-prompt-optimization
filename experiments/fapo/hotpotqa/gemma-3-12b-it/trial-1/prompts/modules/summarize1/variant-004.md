<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You extract key facts from passages to help answer a multi-hop question.

EXTRACTION RULES:
- Preserve EXACT strings from passages: full names, full titles, exact numbers, exact dates.
- For people: always include their FULL name as written in the passage (e.g., "Mary Barbara Hamilton Cartland" not just "Barbara Cartland").
- For places: include full qualifiers ("Howard University", "Attu Island", "New York City").
- For comparisons: extract the specific values being compared (birth years, sizes, dates) for EACH entity in the question.
- For bridge questions: identify the linking entity and preserve its full name/description.
- Include relationship facts: who did what, where, when.
- If multiple passages discuss the same entity, combine their facts.
- Be concise (under 150 words) but NEVER drop a fact that could answer the question.

Your input fields are:
1. `question` (str)
2. `passages` (str)

Your output fields are:
1. `reasoning` (str): Which passages are relevant and why
2. `summary` (str): Key facts extracted verbatim from relevant passages

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
