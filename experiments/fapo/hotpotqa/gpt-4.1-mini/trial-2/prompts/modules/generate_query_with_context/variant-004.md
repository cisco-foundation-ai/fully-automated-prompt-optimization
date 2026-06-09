<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Generate a follow-up search query for the second retrieval hop.

Based on the question and what was found in hop 1, generate a query to find the remaining information. Your query should:
- Include the key entity name discovered in hop 1 (use exact spelling)
- Target the specific missing fact (attribute, date, location still needed)
- Be 3-10 words, using proper nouns and specific terms
- If hop 1 already fully answers the question, generate a verification query using the answer entity

Your input fields are:
1. `question` (str)
2. `summary_1` (str)

Your output fields are:
1. `reasoning` (str): What is still needed to answer the question?
2. `query` (str): Concise search query (3-10 words).

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
