<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Answer the multi-hop question using the two summaries provided. Give only the exact answer.

Your input fields are:
1. `question` (str)
2. `summary_1` (str)
3. `summary_2` (str)

Your output fields are:
1. `reasoning` (str): Your step-by-step reasoning.
2. `answer` (str): The exact answer (1-5 words, no punctuation).

Think through this carefully:
1. What does the question ask for? (a person, place, year, title, yes/no, occupation...)
2. Find that information in the summaries.
3. State ONLY that specific thing as your answer.

Answer rules:
- No periods, no extra words, no quotes
- yes/no questions → "yes" or "no"
- "which is [comparative]" → the entity name only
- "what occupation/type" → singular form
- Character questions → character name/description, not actor
- Film/work questions → title, not person
- Use the fullest name/location from the summaries
- Never say "Not mentioned"

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
