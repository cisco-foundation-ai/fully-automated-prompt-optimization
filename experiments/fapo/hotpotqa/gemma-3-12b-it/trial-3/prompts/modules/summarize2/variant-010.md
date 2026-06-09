<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Combine prior context with new passages. State exact names, dates, and values needed to answer the question. Do not answer the question yet.

For comparison questions: extract the SPECIFIC value for EACH entity separately.
End with: "Answer type needed: [person/title/year/yes-no/occupation/place/number]"

Your input fields are:
1. `question` (str)
2. `context` (str)
3. `passages` (str)

Your output fields are:
1. `reasoning` (str): What new information do the passages add?
2. `summary` (str): All relevant facts from both sources, ending with answer type.

All interactions will be structured in the following way, with the appropriate values filled in.

[[ ## question ## ]]
{question}

[[ ## context ## ]]
{context}

[[ ## passages ## ]]
{passages}

[[ ## reasoning ## ]]
{reasoning}

[[ ## summary ## ]]
{summary}

[[ ## completed ## ]]
In adhering to this structure, your objective is:
        Given the fields `question`, `context`, `passages`, produce the fields `summary`.

User: [[ ## question ## ]]
${question}

[[ ## context ## ]]
${steps.summarize_hop1.output}

[[ ## passages ## ]]
${steps.retrieve_hop2.output}

Respond with the corresponding output fields, starting with the field `[[ ## reasoning ## ]]`, then `[[ ## summary ## ]]`, and then ending with the marker for `[[ ## completed ## ]]`.
