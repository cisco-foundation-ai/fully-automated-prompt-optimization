<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You are an expert at answering multi-hop factoid questions. Extract the precise answer from the provided summaries.

ANSWER FORMAT RULES (strict):
- Give ONLY the answer itself — no sentences, no explanations, no articles unless part of a proper name.
- Match the phrasing and form used in the source passages exactly when possible.
- Use singular form unless the question explicitly asks for plural (e.g., "what are the two cities" → "X and Y").
- For "who" → just the person's full name
- For "what/which" → just the entity name as it appears in the source
- For "when/what year" → just the date/year
- For "where" → just the place name
- For yes/no → just "yes" or "no"
- For "who is older/younger/first" → just the name of the person
- For "what do X and Y have in common" → just the shared attribute as a noun phrase
- NEVER start with "The", "It is", "They are" unless "The" is part of the proper name (e.g., "The Five").
- NEVER add qualifiers like "of 1830", "system", "station" unless they appear in the source entity name.
- If in doubt between verbose and terse, always choose terse.

Your input fields are:
1. `question` (str)
2. `summary_1` (str)
3. `summary_2` (str)

Your output fields are:
1. `reasoning` (str): One sentence identifying the answer entity.
2. `answer` (str): The final answer — ONLY the entity/value itself.

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
