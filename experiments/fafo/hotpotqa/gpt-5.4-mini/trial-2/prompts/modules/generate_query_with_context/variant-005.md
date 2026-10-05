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

INSTRUCTIONS:
Generate a Wikipedia search query to find the SECOND piece of information needed for this multi-hop question.

The first hop (summary_1) found a bridge entity. Now you need to search for additional information about that entity to answer the question.

Rules:
- The query MUST include the bridge entity's name exactly as found in the summary.
- Add keywords that target the SPECIFIC fact the question asks about.
- Keep the query 2-6 words — short and precise.
- Format: "[Entity Name] [attribute/relationship keywords]"
- Examples of good queries: "Gary Pinkel University", "Carhartt headquarters", "Luke Goss drummer Bros"
- NEVER output "cannot be determined", "unknown", or any non-query text.
- If no clear bridge entity was found, reformulate key nouns from the original question as a search query.

User: [[ ## question ## ]]
${question}

[[ ## summary_1 ## ]]
${steps.summarize_hop1.output}

Respond with the corresponding output fields, starting with the field `[[ ## reasoning ## ]]`, then `[[ ## query ## ]]`, and then ending with the marker for `[[ ## completed ## ]]`.
