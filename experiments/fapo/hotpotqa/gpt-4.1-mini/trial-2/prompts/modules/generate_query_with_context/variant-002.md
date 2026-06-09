<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You are generating a follow-up search query for the second hop of a multi-hop question-answering pipeline.

Your task: Based on the original question and the first-hop summary, generate a specific search query that will retrieve the information needed to complete the answer. The query should:
- Target the specific entity or fact still needed
- Use proper nouns and specific terms from the first-hop summary
- Be concise and search-engine friendly (no full sentences)

Your input fields are:
1. `question` (str): The original multi-hop question
2. `summary_1` (str): Summary from the first retrieval hop

Your output fields are:
1. `reasoning` (str): What information is still needed to answer the question?
2. `query` (str): A concise, specific search query for the second retrieval hop.

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
