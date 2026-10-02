<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Answer factoid questions from summaries. Output ONLY the shortest correct answer string.

Rules: yes/no → "yes" or "no". Names → shortest common form. Numbers → as in source. "How many X" → just the number. Comparisons → pick one entity. No sentences, no hedging.

Your input fields are:
1. `question` (str): The multi-hop question to answer.
2. `summary_1` (str): Summary from first retrieval hop.
3. `summary_2` (str): Summary from second retrieval hop.

Your output fields are:
1. `reasoning` (str): Brief chain of reasoning.
2. `answer` (str): Shortest correct factoid.

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
