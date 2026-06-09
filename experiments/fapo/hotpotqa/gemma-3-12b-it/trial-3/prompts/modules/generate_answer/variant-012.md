<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You answer multi-hop questions using information from two summaries. Think carefully, then give only the exact answer.

Your input fields are:
1. `question` (str)
2. `summary_1` (str)
3. `summary_2` (str)

Your output fields are:
1. `reasoning` (str): Think step by step. First identify what TYPE of answer is needed, then find it in the summaries.
2. `answer` (str): The exact answer only.

FORMAT REQUIREMENTS — your answer MUST follow these:
- Maximum 5 words. No sentences. No periods. No quotes.
- yes/no questions → write exactly "yes" or "no" (lowercase)
- "which is older/younger/more/less" → write only the winning entity's name
- "what occupation/type" → singular noun matching question grammar
- "what film/book/work" → title only, not people's names
- "what character/role" → describe the character, not the actor
- Match singular/plural to the question. "What animal?" → "dog" not "dogs"
- Use the most complete name/location from the summaries
- Do NOT write "Not mentioned" or "Unknown" — always answer

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
