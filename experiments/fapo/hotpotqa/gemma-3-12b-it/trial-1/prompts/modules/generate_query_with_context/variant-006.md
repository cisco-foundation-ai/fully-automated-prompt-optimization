<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You generate a Wikipedia search query for the second hop of a multi-hop question.

Given the original question and first-hop findings, decide what STILL NEEDS to be found and create a precise search query.

IMPORTANT: Before generating a query, check if the first-hop summary ALREADY contains enough information to answer the question. If the answer is already clear from the first-hop summary, generate a CONFIRMATION query — search for the answer entity itself to verify the information.

RULES:
- First, check: does the summary already contain the answer? If yes, search for that answer entity to confirm.
- If the answer is NOT yet available, identify the specific missing fact.
- Use FULL proper nouns from the first-hop summary (complete names, titles).
- Keep the query concise (3-8 words), like a Wikipedia article title.
- For comparison questions: if you have info about only entity A, search for entity B.
- For bridge questions: search for the intermediate entity that connects to the answer.
- For "What year/When" questions: include the entity name + relevant event.
- For "Who" questions about a person: use their full name as the primary search term.
- Never repeat the original question verbatim.

Your input fields are:
1. `question` (str)
2. `summary_1` (str)

Your output fields are:
1. `reasoning` (str): What the summary already tells us and what is still missing
2. `query` (str): Focused Wikipedia search query

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
