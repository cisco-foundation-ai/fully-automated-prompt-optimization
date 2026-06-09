<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Generate a Wikipedia search query for the second hop of multi-hop question answering.

You have the original question and findings from the first retrieval hop. Determine what specific piece of information is still missing and craft a search query to find it.

STRATEGY:
- For comparison questions ("who is older", "which has more"): if you found facts about entity A, search for entity B to get comparable facts.
- For bridge questions ("the person who did X, what is their Y"): search for the specific intermediate entity identified in hop 1, using their full proper name.
- Use the FULL proper name of the target entity (e.g., "Rufus Sewell filmography" not just "that actor").
- Aim for 3-8 words. Include the entity name plus the specific attribute you need.
- Think about what Wikipedia article title would contain the missing information.

Your input fields are:
1. `question` (str)
2. `summary_1` (str)

Your output fields are:
1. `reasoning` (str): What is known, what is missing, and what to search
2. `query` (str): Wikipedia-style search query

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
