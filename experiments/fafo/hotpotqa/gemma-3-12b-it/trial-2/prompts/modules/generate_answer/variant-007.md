<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Answer multi-hop questions with the shortest possible correct answer.

RULES:
- Output ONLY: a name, date, number, or yes/no. No sentences. No periods.
- "Which X or Y" → one of them (never "yes"/"no")
- "Who is older/born first" → the one with the EARLIER birth date
- "Who is younger/born last" → the one with the LATER birth date
- July < October < December (earlier month = born first = older)
- Shared-attribute ("what do X and Y both do") → singular noun (e.g., "film director")
- "What [kind of thing] is X" → include the full type (e.g., "car-sharing company")
- "Who was X head coach of" → the team/school name, not the coach
- "This actor appeared in this film" → the film name, not the actor
- For locations → include specificity the question asks for

Your input fields are:
1. `question` (str)
2. `summary_1` (str)
3. `summary_2` (str)
Your output fields are:
1. `reasoning` (str)
2. `answer` (str)
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
