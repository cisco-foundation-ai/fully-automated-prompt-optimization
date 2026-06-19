<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Your input fields are:
1. `question` (str):
2. `context` (str):
3. `passages` (str):
Your output fields are:
1. `reasoning` (str):
2. `summary` (str):
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

This is the SECOND and FINAL retrieval hop. Your summary will be used directly by the answer generation step.

Instructions:
1. Re-read the original question to understand what specific fact or entity is being asked for.
2. The context from hop 1 identified a bridge entity. These new passages were retrieved about that bridge entity.
3. Extract from the new passages the SPECIFIC FACT that answers the question (a name, date, place, number, or attribute).
4. Write a clear summary that states: what the bridge entity is, and what the answer-relevant fact about it is.

Rules:
- Use exact names, dates, and numbers from the passages.
- For comparison questions, clearly state the relevant attributes for both entities.
- Do NOT attempt to answer the question — but DO highlight which fact from the passages directly addresses what the question asks.
- Never say "cannot be determined" — always report the available facts.

User: [[ ## question ## ]]
${question}

[[ ## context ## ]]
${steps.summarize_hop1.output}

[[ ## passages ## ]]
${steps.retrieve_hop2.output}

Respond with the corresponding output fields, starting with the field `[[ ## reasoning ## ]]`, then `[[ ## summary ## ]]`, and then ending with the marker for `[[ ## completed ## ]]`.
