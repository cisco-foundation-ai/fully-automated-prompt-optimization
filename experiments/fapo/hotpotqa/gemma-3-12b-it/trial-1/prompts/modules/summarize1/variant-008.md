<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Extract key facts from passages to answer a multi-hop question.

Read the passages and extract ALL information relevant to the question. Focus on:
- Full names (including middle names, birth names, full titles)
- Dates, numbers, years
- Occupations, roles, relationships
- Locations with full qualifiers (e.g., "Howard University", not "Howard")
- For comparison questions: extract comparable values for EACH entity mentioned

Be thorough — missing a fact could lose the correct answer. Use exact wording from passages.

Your input fields are:
1. `question` (str)
2. `passages` (str)

Your output fields are:
1. `reasoning` (str): Identify relevant passages
2. `summary` (str): All relevant facts extracted from passages

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
