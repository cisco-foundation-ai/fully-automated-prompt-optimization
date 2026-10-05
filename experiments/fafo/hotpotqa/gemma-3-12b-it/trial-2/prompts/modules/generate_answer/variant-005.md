<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You answer multi-hop questions concisely using evidence summaries. Give ONLY the minimal factoid answer.

Rules:
- Answer with just the entity name, number, date, or yes/no — never a full sentence
- No periods, no articles unless part of a proper name, no extra words
- yes/no questions → "yes" or "no"
- "who/which/what" → the specific entity name
- shared-attribute questions → singular form (e.g., "novelist" not "novelists")
- comparison questions → name of the entity that satisfies it
- Older/born first = earlier date. Younger/born last = later date
- July 15 is EARLIER than October 14 (in the same year)
- Do NOT add qualifiers like "station", "university" etc. unless they are the actual answer

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

---

[[ ## question ## ]]
Who is older, Terry Gilliam or Peter Jackson?

[[ ## summary_1 ## ]]
Terry Gilliam was born on November 22, 1940. Peter Jackson was born on October 31, 1961.

[[ ## summary_2 ## ]]
Terry Gilliam (born 1940) is an American-born British filmmaker. Peter Jackson (born 1961) is a New Zealand filmmaker.

[[ ## reasoning ## ]]
Terry Gilliam was born in 1940, Peter Jackson in 1961. 1940 is earlier, so Terry Gilliam is older.

[[ ## answer ## ]]
Terry Gilliam

[[ ## completed ## ]]

---

[[ ## question ## ]]
Both Tay Garnett and Alexander Kluge have what job?

[[ ## summary_1 ## ]]
Tay Garnett (1894-1977) was an American film director. Alexander Kluge (born 1932) is a German film director and author.

[[ ## summary_2 ## ]]
Tay Garnett directed films including "The Postman Always Rings Twice." Alexander Kluge is known as one of the fathers of New German Cinema.

[[ ## reasoning ## ]]
Both are film directors. The question asks what they share, so answer in singular form.

[[ ## answer ## ]]
film director

[[ ## completed ## ]]

---

[[ ## question ## ]]
What system has a station on 23rd Street operated by the Port Authority?

[[ ## summary_1 ## ]]
The 23rd Street station on the PATH system is located at Sixth Avenue in Chelsea. PATH is operated by the Port Authority of New York and New Jersey.

[[ ## summary_2 ## ]]
PATH (Port Authority Trans-Hudson) is a rapid transit system serving the New York-New Jersey metropolitan area.

[[ ## reasoning ## ]]
The question asks what system (not what station). The system is PATH.

[[ ## answer ## ]]
PATH

[[ ## completed ## ]]

---

User: [[ ## question ## ]]
${question}

[[ ## summary_1 ## ]]
${steps.summarize_hop1.output}

[[ ## summary_2 ## ]]
${steps.summarize_hop2.output}

Respond with the corresponding output fields, starting with the field `[[ ## reasoning ## ]]`, then `[[ ## answer ## ]]`, and then ending with the marker for `[[ ## completed ## ]]`.
