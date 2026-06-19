<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Extract the factoid answer from the summaries below. Your answer must be a short entity (1-5 words).

RULES:
- Output ONLY the answer entity. No explanation.
- Answer what the question asks for — if it asks for a film, give the film name; if a person, give the person's name.
- Singular form unless the question asks for a list ("professional wrestler" not "professional wrestlers").
- Drop suffixes like Inc., Corp., F.C. ("AT&T" not "AT&T Inc.").
- Include year in dates ("August 2, 1973" not "August 2").
- For "Are both.../Did both.../Is X also..." → answer only "yes" or "no".
- Give ONE answer only, unless the question explicitly asks to list multiple things.
- Never start with "The", "Both", or "A".

Your input fields are:
1. `question` (str)
2. `summary_1` (str)
3. `summary_2` (str)

Your output fields are:
1. `reasoning` (str): What does the question ask for? What entity in the summaries answers it?
2. `answer` (str): 1-5 word answer.

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
