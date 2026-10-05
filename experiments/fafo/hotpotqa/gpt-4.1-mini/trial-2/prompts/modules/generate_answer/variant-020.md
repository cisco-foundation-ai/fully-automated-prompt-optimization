<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Answer the multi-hop factoid question using ONLY the two summaries below. Output a short entity (1-5 words).

RULES:
- Give ONLY the answer — no sentences, no explanation.
- Identify what the question asks for (a person? film? place? year?) and answer with THAT type of entity.
- "Are both.../Did both.../Is X also..." → answer "yes" or "no" only.
- Singular: "professional wrestler" not "professional wrestlers".
- Strip suffixes: "AT&T" not "AT&T Inc.", "PATH" not "PATH system".
- Full dates: "August 2, 1973" not "August 2".
- ONE entity only unless the question asks for multiple.
- Never start with "The" (unless proper name), "Both", or "A".
- If the summary says "The answer is: [X]", use [X] directly (unless it violates above rules).

Your input fields are:
1. `question` (str)
2. `summary_1` (str)
3. `summary_2` (str)

Your output fields are:
1. `reasoning` (str): The question asks for [type]. The answer is [entity].
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
