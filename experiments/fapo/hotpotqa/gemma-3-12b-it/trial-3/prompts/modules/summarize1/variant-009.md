<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Extract relevant facts from passages to help answer the question. State exact names, dates, and values. Do not answer the question yet.

For comparison questions ("who is older", "which has more", "are both"): extract the SPECIFIC value for EACH entity separately (e.g., "Entity A: born 1943. Entity B: born 1945."). Do not state which is greater.

Your input fields are:
1. `question` (str)
2. `passages` (str)

Your output fields are:
1. `reasoning` (str): Which passages are relevant and why.
2. `summary` (str): Key facts extracted.

All interactions will be structured in the following way, with the appropriate values filled in.

[[ ## question ## ]]
{question}

[[ ## passages ## ]]
{passages}

[[ ## reasoning ## ]]
{reasoning}

[[ ## summary ## ]]
{summary}

[[ ## completed ## ]]
In adhering to this structure, your objective is:
        Given the fields `question`, `passages`, produce the fields `summary`.

User: [[ ## question ## ]]
${question}

[[ ## passages ## ]]
${steps.retrieve_hop1.output}

Respond with the corresponding output fields, starting with the field `[[ ## reasoning ## ]]`, then `[[ ## summary ## ]]`, and then ending with the marker for `[[ ## completed ## ]]`.
