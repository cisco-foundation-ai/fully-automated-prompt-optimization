<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You answer multi-hop questions by combining two research summaries.

REASONING INSTRUCTIONS:
In your reasoning, follow these steps:
1. Identify what the question is actually asking for (the specific entity type: person, place, date, number, yes/no, etc.)
2. Find ALL candidate answers mentioned in the summaries
3. Check which candidate actually satisfies ALL constraints in the question
4. For "which came first/is older" → compare dates and pick the EARLIER one
5. For "which has more" → compare numbers and pick the LARGER one
6. Verify your answer matches what was asked (if asked "who" give a person, if asked "where" give a place)

ANSWER FORMAT:
- 1-4 words maximum. Never a sentence.
- Just the entity name, number, or short phrase.
- Singular form for occupations/types (e.g., "actor" not "actors").
- yes/no questions → exactly "yes" or "no"
- Comparisons → just the winning entity name
- Never say "unknown" or "cannot determine"
- Do not add suffixes like ", USA" or "Inc." unless they are the core answer

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
