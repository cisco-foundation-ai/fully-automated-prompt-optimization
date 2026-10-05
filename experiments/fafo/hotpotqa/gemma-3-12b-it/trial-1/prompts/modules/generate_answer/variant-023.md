<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Answer the question using ONLY the summaries. Give a short factoid answer.

Rules:
- No sentences or periods. Just the answer.
- Yes/no questions → "yes" or "no"
- "Will/Would X or Y...?" → choose X or Y (not yes/no)
- Comparisons → entity name only. Born later = younger.
- "How many" → number only
- SINGULAR for categories: "dog" not "dogs", "engineer" not "engineers"
- Complete entity names: "Howard University" not "Howard"
- People's names: most common form in evidence
- Lists: "X and Y"
- Bridge questions: answer what was ASKED (film, institution, company — not the person)
- Guess if unsure

Your input fields are:
1. `question` (str)
2. `summary_1` (str)
3. `summary_2` (str)

Your output fields are:
1. `reasoning` (str): Brief reasoning
2. `answer` (str): Factoid answer

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

User: [[ ## question ## ]]
${question}

[[ ## summary_1 ## ]]
${steps.summarize_hop1.output}

[[ ## summary_2 ## ]]
${steps.summarize_hop2.output}

Respond with the corresponding output fields, starting with the field `[[ ## reasoning ## ]]`, then `[[ ## answer ## ]]`, and then ending with the marker for `[[ ## completed ## ]]`.
