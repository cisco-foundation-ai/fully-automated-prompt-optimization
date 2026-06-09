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

INSTRUCTIONS:
This is the SECOND hop. You have context from hop 1 and new passages from hop 2.

Your summary will be passed directly to the answer generation step, so it must contain ALL the information needed to produce the correct short answer.

Steps:
1. Re-read the original question to determine exactly what fact is needed.
2. Check if the context from hop 1 already contains the answer.
3. Check if the new passages contain additional facts that complete the answer.
4. Compile a clear summary with these facts, using exact quotes for names, numbers, and dates.

Rules:
- Use EXACT names, numbers, and dates as they appear in the passages.
- For person names, include both the full formal name and common name if both appear (e.g., "Luke Damon Goss, known as Luke Goss").
- For comparison questions, clearly state the relevant attribute for BOTH entities.
- Include the specific fact that answers the question, even if it seems obvious from context.
- NEVER say "cannot be determined" — always report the most relevant facts available.

User: [[ ## question ## ]]
${question}

[[ ## context ## ]]
${steps.summarize_hop1.output}

[[ ## passages ## ]]
${steps.retrieve_hop2.output}

Respond with the corresponding output fields, starting with the field `[[ ## reasoning ## ]]`, then `[[ ## summary ## ]]`, and then ending with the marker for `[[ ## completed ## ]]`.
