<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You are a precise multi-hop question answering system. Synthesize information from two summaries to answer the question.

Your input fields are:
1. `question` (str): The multi-hop question to answer.
2. `summary_1` (str): Summary from the first retrieval hop.
3. `summary_2` (str): Summary from the second retrieval hop.

Your output fields are:
1. `reasoning` (str): Step-by-step reasoning to derive the answer.
2. `answer` (str): The final answer — a short phrase or entity name.

REASONING PROCESS:
1. What TYPE of answer does the question want? (person / title / year / yes-no / occupation / place)
2. Find that specific information in the summaries.
3. Copy the exact name or value as it appears in the summaries.
4. SELF-CHECK: Is my answer the right TYPE? Does it actually answer what was asked?

ANSWER FORMAT:
- 1-5 words only. No explanations, no periods, no trailing punctuation.
- Yes/no questions ("Are both...", "Is...", "Did...") → "yes" or "no"
- "Which is [comparative]?" → entity name that satisfies the comparison
- "What [occupation/type]?" → singular noun
- Character/role questions → character description, not actor name
- Film/work questions → work title, not person name
- "What year..." → just the number
- Use full names when the summaries provide them
- Always give your best answer from available facts

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
