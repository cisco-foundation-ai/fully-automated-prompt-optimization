<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Your input fields are:
1. `question` (str):
2. `context` (str):
3. `passages` (str):
Your output fields are:
1. `reasoning` (str):
2. `summary` (str):
All interactions will be structured in the following way, with the appropriate values filled in.

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
In adhering to this structure, your objective is:
        Given the fields `question`, `context`, `passages`, produce the fields `summary`.
        Combine information from the first-hop context and the new passages to build a complete factual picture. Your summary MUST:
        1. Start with "ANSWER: [entity]" on the first line if you can identify the answer to the question.
        2. Then include ALL specific details: full names (with middle names as given), dates, numbers, titles, locations, occupations, and relationships.
        3. Preserve exact wording from sources for proper nouns and factual claims.
        4. For comparison questions: state both entities' comparable values and which one wins.
        5. Do not omit potentially relevant details — the answer module relies entirely on your summary.

User: [[ ## question ## ]]
${question}

[[ ## context ## ]]
${steps.summarize_hop1.output}

[[ ## passages ## ]]
${steps.retrieve_hop2.output}

Respond with the corresponding output fields, starting with the field `[[ ## reasoning ## ]]`, then `[[ ## summary ## ]]`, and then ending with the marker for `[[ ## completed ## ]]`.
