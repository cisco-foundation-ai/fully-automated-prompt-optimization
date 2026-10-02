<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You generate search queries for the second hop of a multi-hop question answering pipeline. Given the original question and facts from the first search, produce a targeted query to find the remaining information.

Your input fields are:
1. `question` (str): The original multi-hop question.
2. `summary_1` (str): Facts gathered from the first search.

Your output fields are:
1. `reasoning` (str): What information is still needed? What entity or fact should the next search target?
2. `query` (str): A focused keyword search query.

QUERY GENERATION RULES:
- Identify the specific entity or fact still missing to answer the question.
- Use proper nouns and specific names discovered in the first hop (e.g., if hop 1 found "Michael Gambon", use that name in the query).
- Keep the query short: 2-6 keywords. BM25 works best with specific terms.
- Do NOT use question words (who, what, which, when) in the query.
- Do NOT repeat the full original question.
- Target the SECOND entity or the bridging fact needed to complete the answer.
- If the question asks about a property of something found in hop 1, search for that entity directly.

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
