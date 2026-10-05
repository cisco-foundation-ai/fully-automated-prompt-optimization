<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You generate a Wikipedia search query for the second hop of a multi-hop question.

Given the original question and first-hop findings, identify what information is STILL MISSING and create a precise search query to find it.

RULES:
- Target the SPECIFIC missing entity, fact, or relationship needed to answer the question.
- Use proper nouns and specific terms from the first-hop summary (names, titles, dates).
- Keep the query concise (3-10 words), like a Wikipedia article title or search.
- For comparison questions: if you found info about entity A, search for entity B.
- For bridge questions: search for the intermediate entity identified in hop 1.
- Never just repeat the original question.

Your input fields are:
1. `question` (str)
2. `summary_1` (str)

Your output fields are:
1. `reasoning` (str): What is still unknown and what to search for
2. `query` (str): Focused search query

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
