<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Answer the following multi-hop question using ONLY the information in the summaries below.

Output ONLY the answer — never a sentence. The answer should be:
- A person's name (e.g., "Peter Gabriel")
- A place name (e.g., "Dearborn, Michigan")
- A date (e.g., "May 15, 1940" or "1950")
- A number (e.g., "267,785")
- A thing/concept (e.g., "film director" or "PATH")
- "yes" or "no" for yes/no questions

Keep it SHORT: use the common name, drop unnecessary suffixes (Inc., FC, etc.), use singular unless the question asks for multiple items. Never begin with "The" unless part of a title.

Your input fields are:
1. `question` (str)
2. `summary_1` (str)
3. `summary_2` (str)

Your output fields are:
1. `reasoning` (str): What does the question ask for? What entity in the summaries answers it?
2. `answer` (str): The answer (1-5 words max).

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
