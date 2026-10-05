<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Answer the multi-hop question using the provided summaries. Give ONLY the short answer — a name, number, date, or yes/no.

Rules:
- Yes/no questions → answer "yes" or "no"
- "Who/which is [comparative]" → the entity name only
- "What [category]" → singular noun (e.g., "dog", "film director", "engineer")
- Include full entity names with qualifiers (e.g., "Howard University" not "Howard")
- Join lists with "and" (e.g., "A and B")
- No periods, no extra words, no explanations in the answer
- Always answer — never say "cannot be determined"

Your input fields are:
1. `question` (str)
2. `summary_1` (str)
3. `summary_2` (str)

Your output fields are:
1. `reasoning` (str): Brief reasoning
2. `answer` (str): Short answer

[[ ## question ## ]]
{question}

[[ ## summary_1 ## ]]
{summary_1}

[[ ## summary_2 ## ]]
{summary_2}

[[ ## reasoning ## ]]
{reasoning}

[[ ## answer ## ]]
{answer}

[[ ## completed ## ]]

User: [[ ## question ## ]]
${question}

[[ ## summary_1 ## ]]
${steps.summarize_hop1.output}

[[ ## summary_2 ## ]]
${steps.summarize_hop2.output}

Respond with the corresponding output fields, starting with the field `[[ ## reasoning ## ]]`, then `[[ ## answer ## ]]`, and then ending with the marker for `[[ ## completed ## ]]`.
