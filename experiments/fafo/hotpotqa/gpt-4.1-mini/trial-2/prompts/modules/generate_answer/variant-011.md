<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Extract the final answer from the summaries below. Output ONLY the answer — 1-5 words maximum. Never a sentence.

Look for "ANSWER:" in summary_2 — if present, output exactly what follows it.
Otherwise, identify the answer entity from the summaries.

Rules:
- Use the shortest common form of names
- Drop corporate/organizational suffixes (Inc., FC, Corp.)
- For yes/no questions: just "yes" or "no"
- For comparisons: just the entity name
- For shared traits: singular noun (e.g., "film director")
- Never start with "The" unless it's part of a title

Your input fields are:
1. `question` (str)
2. `summary_1` (str)
3. `summary_2` (str)

Your output fields are:
1. `reasoning` (str): The answer is...
2. `answer` (str): [answer only, 1-5 words]

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
