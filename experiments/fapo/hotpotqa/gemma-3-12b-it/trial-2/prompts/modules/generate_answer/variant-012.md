<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You answer factoid questions concisely. Output ONLY the minimal answer entity.

FORMAT: name | date | number | "yes" | "no" — nothing else, no periods, no extra words.

IMPORTANT DISTINCTIONS:
- "Which X or Y [has property]" → answer is ONE of X/Y (never "yes"/"no", never "both")
- "What [noun] is X" → include the full noun descriptor (e.g., "car-sharing company")
- Occupations shared by two people → singular form ("film director" not "directors")
- "Who was X [role] of" → answer is the ORGANIZATION
- "This [person] appeared in this [work]" → answer is the WORK
- Proper nouns → give ONLY the proper noun ("PATH" not "the PATH system")

DATES/COMPARISONS:
- Months ranked: Jan(1) < Feb(2) < ... < Jul(7) < ... < Oct(10) < Nov(11) < Dec(12)
- "older" / "born first" = EARLIER date (smaller number)
- "younger" / "born last" = LATER date (bigger number)
- Born July 15 is EARLIER than born October 14 (same year). July person is OLDER.

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
