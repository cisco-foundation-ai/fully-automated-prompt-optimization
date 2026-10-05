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
You must generate a Wikipedia search query to find the MISSING information needed to answer the original question.

Step 1: What does the question ultimately ask for?
Step 2: What did the first hop find (the bridge entity)?
Step 3: What additional fact about the bridge entity do we still need?

Query format rules:
- Use the bridge entity's FULL NAME as found in summary_1.
- Add 1-3 keywords describing what fact is needed (e.g., birth date, headquarters, occupation).
- Keep the query 2-8 words long, suitable for Wikipedia search.
- NEVER output "cannot be determined" or "unknown" — always produce a searchable query.
- If summary_1 found the bridge entity, search for the missing attribute of that entity.
- If summary_1 didn't find a clear bridge entity, try reformulating the original question as a search query.

User: [[ ## question ## ]]
${question}

[[ ## summary_1 ## ]]
${steps.summarize_hop1.output}

Respond with the corresponding output fields, starting with the field `[[ ## reasoning ## ]]`, then `[[ ## query ## ]]`, and then ending with the marker for `[[ ## completed ## ]]`.
