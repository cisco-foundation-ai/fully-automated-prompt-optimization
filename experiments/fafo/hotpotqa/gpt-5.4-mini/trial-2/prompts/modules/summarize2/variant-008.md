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

This is the SECOND and FINAL retrieval hop. Your summary feeds directly into the answer step.

GOAL: Produce a summary that makes extracting the correct short answer trivial.

Steps:
1. Determine what the question asks for (person, place, date, number, yes/no).
2. Find the bridge entity from the context.
3. Find the specific answer fact in the new passages about the bridge entity.
4. Write a concise summary combining both hops' findings.
5. End with: "ANSWER: [the specific short answer]"

Rules:
- Use exact names, dates, and numbers from the passages.
- For yes/no questions, state the evidence and conclude "ANSWER: yes" or "ANSWER: no".
- For person names, use the full name as written in the passages.
- For comparisons, state both entities' attributes and which satisfies the question.
- Never say "cannot be determined". Always give your best answer from available info.

User: [[ ## question ## ]]
${question}

[[ ## context ## ]]
${steps.summarize_hop1.output}

[[ ## passages ## ]]
${steps.retrieve_hop2.output}

Respond with the corresponding output fields, starting with the field `[[ ## reasoning ## ]]`, then `[[ ## summary ## ]]`, and then ending with the marker for `[[ ## completed ## ]]`.
