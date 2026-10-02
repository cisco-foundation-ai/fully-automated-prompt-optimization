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

IMPORTANT INSTRUCTIONS:
- Identify what information is still MISSING to answer the original question.
- Generate a short, specific search query (2-8 words) targeting that missing information.
- Use the most specific entity name found in summary_1 as the basis of your query.
- The query should be suitable for searching Wikipedia — use entity names and key attributes.
- If the summary already contains the final answer, generate a query to VERIFY it by searching for the key entity.
- NEVER output "cannot be determined" or similar — always generate a search query even if the first hop was incomplete.

User: [[ ## question ## ]]
${question}

[[ ## summary_1 ## ]]
${steps.summarize_hop1.output}

Respond with the corresponding output fields, starting with the field `[[ ## reasoning ## ]]`, then `[[ ## query ## ]]`, and then ending with the marker for `[[ ## completed ## ]]`.
