<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Generate a search query for the second hop of a multi-hop question.

You know the original question and what was found in the first retrieval. Now generate a SHORT, SPECIFIC query to find the remaining information needed.

QUERY RULES:
- Use 3-8 words maximum
- Include the specific entity name discovered in hop 1
- Target the missing fact (the attribute, date, location, etc. still needed)
- Never write a full sentence — just search keywords
- If the first summary already fully answers the question, still generate a query to verify or expand

Your input fields are:
1. `question` (str): The original question
2. `summary_1` (str): What was found in the first hop

Your output fields are:
1. `reasoning` (str): What specific fact is still needed?
2. `query` (str): Short keyword query (3-8 words).

[[ ## question ## ]]
{question}

[[ ## summary_1 ## ]]
{summary_1}

[[ ## reasoning ## ]]
{reasoning}

[[ ## query ## ]]
{query}

[[ ## completed ## ]]

User: [[ ## question ## ]]
${question}

[[ ## summary_1 ## ]]
${steps.summarize_hop1.output}

Respond with the corresponding output fields, starting with the field `[[ ## reasoning ## ]]`, then `[[ ## query ## ]]`, and then ending with the marker for `[[ ## completed ## ]]`.
