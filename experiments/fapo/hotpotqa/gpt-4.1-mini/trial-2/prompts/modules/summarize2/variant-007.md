<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You are the final synthesis step. Combine first-hop context with second-hop passages to answer the question.

INSTRUCTIONS:
1. Identify which passage(s) connect to the first-hop context
2. Determine the precise answer entity
3. State ONLY: the connection in 1 sentence, then "The answer is: [X]"

X should be the EXACT entity/value from the passages — use the shortest common name form. For yes/no, just "yes" or "no". For comparisons, just the name. Do NOT add "Inc.", "FC", or other suffixes unless part of the entity name in the passages.

Your input fields are:
1. `question` (str)
2. `context` (str)
3. `passages` (str)

Your output fields are:
1. `reasoning` (str): Connection between hops and the answer.
2. `summary` (str): One sentence of context, then "The answer is: [X]"

[[ ## question ## ]]
{question}

[[ ## context ## ]]
{context}

[[ ## passages ## ]]
{passages}

[[ ## reasoning ## ]]
{reasoning}

[[ ## summary ## ]]
{summary}

[[ ## completed ## ]]

User: [[ ## question ## ]]
${question}

[[ ## context ## ]]
${steps.summarize_hop1.output}

[[ ## passages ## ]]
${steps.retrieve_hop2.output}

Respond with the corresponding output fields, starting with the field `[[ ## reasoning ## ]]`, then `[[ ## summary ## ]]`, and then ending with the marker for `[[ ## completed ## ]]`.
