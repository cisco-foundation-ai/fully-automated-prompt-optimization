<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Your input fields are:
1. `question` (str):
2. `summary_1` (str):
Your output fields are:
1. `reasoning` (str):
2. `query` (str):
All interactions will be structured in the following way, with the appropriate values filled in.

[[ ## question ## ]]
{question}

[[ ## summary_1 ## ]]
{summary_1}

[[ ## reasoning ## ]]
{reasoning}

[[ ## query ## ]]
{query}

[[ ## completed ## ]]
In adhering to this structure, your objective is:
        Given the fields `question`, `summary_1`, produce the fields `query`.

You are generating a BM25 search query to find the SECOND piece of information for a multi-hop question.

The first hop found a bridge entity in summary_1. Now generate a query to find additional information.

RULES:
1. The query MUST start with the bridge entity's name (copy it EXACTLY from the summary, including full name).
2. After the entity name, add 1-3 keywords targeting the specific fact the question needs.
3. Total query length: 2-7 words.
4. Use only nouns and proper names — no verbs, no question words.
5. If the question asks "who", query for the entity + their role/relationship keyword.
6. If the question asks about a date/year, query for entity + event keyword.
7. If the question asks for a comparison, query for the SECOND entity that needs comparison.

NEVER output reasoning, explanations, or anything besides the query in the query field.

User: [[ ## question ## ]]
${question}

[[ ## summary_1 ## ]]
${steps.summarize_hop1.output}

Respond with the corresponding output fields, starting with the field `[[ ## reasoning ## ]]`, then `[[ ## query ## ]]`, and then ending with the marker for `[[ ## completed ## ]]`.
