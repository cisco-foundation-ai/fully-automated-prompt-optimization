<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Answer the question using the provided evidence. Output ONLY the answer — a short factoid (name, date, number, or yes/no).

RULES:
- Shortest possible answer. No periods. No full sentences. No extra qualifiers.
- "Which X or Y" → one of them, not "yes" or "no"
- "Who is older" → the one born EARLIER (lower year, or earlier month in same year: Jul < Oct)
- "Who is younger" → the one born LATER
- Shared traits ("what do X and Y both do") → singular form ("film director", "novelist")
- "What type/kind is X" → include the descriptor ("car-sharing company", "professional wrestler")
- "Who was X head coach of" → the TEAM name
- "This actor in this film" → the FILM name
- "What system/service" → proper noun only ("PATH" not "PATH station")
- City answers → city name only (not "city, state") unless state IS the answer

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
