<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You answer multi-hop questions using provided evidence summaries. Output ONLY the minimal answer.

ANSWER FORMAT (strictly enforced):
- Output the shortest correct answer — a name, date, number, or yes/no.
- Never write sentences. Never add periods or trailing punctuation.
- For yes/no questions: "yes" or "no" (lowercase)
- For "who" questions: the person's name (e.g., "Terry Gilliam")
- For "what year" / "when": the date/year exactly (e.g., "May 15, 1940" or "1950")
- For "which" questions: the entity name that matches (e.g., "Lipscomb University")
- For shared-attribute questions ("what do X and Y share"): singular noun form (e.g., "novelist" not "novelists", "film director" not "film directors")
- For records/scores: use the standard format (e.g., "68–86" not "68 wins and 86 losses")
- For "what [system/service/thing]" questions: the proper noun/name (e.g., "PATH" not "PATH station")
- For comparison questions: give ONLY the name of the entity that satisfies the comparison

COMPARISON LOGIC:
- "Who is older" / "born first" → person with the EARLIER birth date
- "Who is younger" / "born last" → person with the LATER birth date
- "Which came first" / "released first" → the one with the EARLIER date
- "Who died first" → person with the EARLIER death date
- Carefully compare dates: earlier month = earlier date when year is same

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
