<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Answer the question using the summaries. The answer must be 1-5 words — just the entity, name, date, number, or yes/no. Never write a sentence.

Your input fields are:
1. `question` (str):
2. `summary_1` (str):
3. `summary_2` (str):
Your output fields are:
1. `reasoning` (str):
2. `answer` (str):
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
        Rules: (1) answer = shortest correct span, 1-5 words (2) yes/no for yes/no questions (3) singular form for categories (4) the bridge entity used for retrieval is often NOT the answer (5) never say "cannot be determined"

User: [[ ## question ## ]]
${question}

[[ ## summary_1 ## ]]
${steps.summarize_hop1.output}

[[ ## summary_2 ## ]]
${steps.summarize_hop2.output}

Respond with the corresponding output fields, starting with the field `[[ ## reasoning ## ]]`, then `[[ ## answer ## ]]`, and then ending with the marker for `[[ ## completed ## ]]`.
