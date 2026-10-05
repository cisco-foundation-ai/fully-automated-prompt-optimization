<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Answer the question with the SHORTEST possible factoid. Rules:
- yes/no → "yes" or "no" (one word, lowercase)
- Person → shortest common name (e.g., "Ernest II")
- Place → city name only (e.g., "Las Vegas" not "Las Vegas, Nevada")
- Occupation → singular (e.g., "wrestler" not "wrestlers")
- Date/number → exact form from source
- Entity → just the name, no descriptors
- Comparison ("which is X-er, A or B?") → just "A" or "B"
- NEVER use full sentences, never add articles or qualifiers

Your input fields are:
1. `question` (str)
2. `summary_1` (str)
3. `summary_2` (str)

Your output fields are:
1. `reasoning` (str): What does the question ask for? Extract from summaries.
2. `answer` (str): Bare factoid.

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
