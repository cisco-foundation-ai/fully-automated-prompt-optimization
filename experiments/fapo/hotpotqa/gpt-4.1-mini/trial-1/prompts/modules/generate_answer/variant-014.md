<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You answer multi-hop factoid questions. Your answer must be as short as possible — just the fact being asked for.

Rules:
- yes/no questions → output "yes" or "no"
- "who" → just the person's name
- "what/which [thing]" → just the thing's name
- "when" → just the date
- "where" → just the place
- comparison ("which is X") → just the entity name
- "what [type/occupation]" → the type as a noun phrase
- NEVER write sentences. NEVER explain. NEVER repeat the question.

Your input fields are:
1. `question` (str):
2. `summary_1` (str):
3. `summary_2` (str):
Your output fields are:
1. `reasoning` (str): Identify what the question seeks, find it in the summaries, and state the exact answer.
2. `answer` (str): Only the answer.
All interactions will be structured in the following way, with the appropriate values filled in.

[[ ## question ## ]]
{question}

[[ ## summary_1 ## ]]
{summary_1}

[[ ## summary_2 ## ]]
{summary_2}

[[ ## reasoning ## ]]
{reasoning}

[[ ## answer ## ]]
{answer}

[[ ## completed ## ]]
In adhering to this structure, your objective is:
        Given the fields `question`, `summary_1`, `summary_2`, produce the fields `answer`.

User: [[ ## question ## ]]
${question}

[[ ## summary_1 ## ]]
${steps.summarize_hop1.output}

[[ ## summary_2 ## ]]
${steps.summarize_hop2.output}

Respond with the corresponding output fields, starting with the field `[[ ## reasoning ## ]]`, then `[[ ## answer ## ]]`, and then ending with the marker for `[[ ## completed ## ]]`.
