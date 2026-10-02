<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Generate a follow-up search query for the second retrieval hop in a multi-hop QA pipeline.

You have the original question and a summary from the first hop. Generate a search query to find the REMAINING information needed to answer the question.

STRATEGY:
1. Identify what the question ULTIMATELY asks for (the final answer type: a person, place, year, film, etc.)
2. Identify what the first hop found (the bridge entity)
3. Generate a query that uses the bridge entity to find the final answer

QUERY RULES:
- 3-8 words maximum
- Use the EXACT entity name found in hop 1 (proper nouns, correct spelling)
- Target the specific attribute/fact still needed
- Use Wikipedia-style search terms (entity names + key attribute)
- Do NOT repeat the whole question — focus on what's MISSING

Your input fields are:
1. `question` (str)
2. `summary_1` (str)

Your output fields are:
1. `reasoning` (str): What bridge entity was found? What specific fact is still needed?
2. `query` (str): Search query (3-8 words).

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
