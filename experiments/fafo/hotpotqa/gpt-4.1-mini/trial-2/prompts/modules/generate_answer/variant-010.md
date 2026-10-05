<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Extract the answer to a multi-hop factoid question from the summaries.

CRITICAL: Your answer must be 1-5 words. Never write a sentence.

Rules:
- Person → their name only (e.g., "Peter Gabriel")
- Place → place name only (e.g., "Dearborn, Michigan")  
- Date → the date (e.g., "May 15, 1940")
- Yes/No → "yes" or "no"
- Comparison → just the winner's name
- Shared trait → singular noun (e.g., "film director")
- Thing → its shortest common name, no suffixes like Inc./FC/system

If the summaries say "The answer is: X" — just output X.

Your input fields are:
1. `question` (str)
2. `summary_1` (str)
3. `summary_2` (str)

Your output fields are:
1. `reasoning` (str): The answer entity is...
2. `answer` (str): [1-5 words only]

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
