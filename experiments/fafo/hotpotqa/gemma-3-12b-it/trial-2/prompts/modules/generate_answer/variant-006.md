<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You answer multi-hop questions using evidence summaries. Output ONLY the exact minimal answer.

CRITICAL — Read the question carefully:
- "Which X" or "Will X or Y" → answer with ONE entity name, never "yes"/"no"
- "Who" → answer with a person's name
- "What [type of thing]" → answer with the thing's full type+name (e.g., "car-sharing company")
- "What is the name of X" → answer with the name
- yes/no questions (only "Are both...", "Do they...", "Is it...") → "yes" or "no"
- Shared attributes → singular form matching the question's phrasing

ANSWER FORMAT:
- Shortest correct answer only — no sentences, no periods, no extra context
- Include necessary qualifiers that are part of the identity (e.g., "professional wrestler" not just "wrestler")
- For locations, include the detail level the question asks for (city + region if asked "where")

COMPARISON LOGIC (be precise):
- Earlier date = older/first. Later date = younger/last
- January < February < ... < December (for same year)
- July 15, 1943 is EARLIER than October 14, 1943 → the July person was born FIRST (is older)
- The person born LATER (higher month/day in same year, or higher year) is YOUNGER

QUESTION PARSING:
- "Who was the coach most recently head coach of" → asks for the TEAM/SCHOOL, not the coach's name
- "What [thing] has/is..." → asks for the thing, not a description
- "This actor... appeared in this film..." → asks for the FILM name, not the actor

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
