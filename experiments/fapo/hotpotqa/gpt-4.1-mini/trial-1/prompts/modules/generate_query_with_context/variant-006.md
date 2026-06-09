<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You are generating a Wikipedia search query for the second hop of a multi-hop question. You have the original question and a summary from the first hop. Your query must retrieve the specific missing piece of information needed to answer the question.

Rules:
- The query should be a short Wikipedia-style search query (2-5 words ideal).
- Use the most specific entity name or title from the first hop's summary.
- Target the exact entity or fact that is still missing to answer the original question.
- Do NOT repeat the full question as your query.
- Do NOT use question words (who, what, when, where, which) in the query.
- If the summary already contains the answer, still generate a query for the most relevant entity to verify.
- Prefer proper nouns and specific names over generic descriptions.

Your input fields are:
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

User: [[ ## question ## ]]
${question}

[[ ## summary_1 ## ]]
${steps.summarize_hop1.output}

Respond with the corresponding output fields, starting with the field `[[ ## reasoning ## ]]`, then `[[ ## query ## ]]`, and then ending with the marker for `[[ ## completed ## ]]`.
