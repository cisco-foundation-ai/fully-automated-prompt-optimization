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
1. Re-read the original question. Determine exactly what TYPE of answer is needed (a person's name, a date, a place, yes/no, etc.)
2. The context from hop 1 identified a bridge entity. These new passages were retrieved about that bridge entity.
3. Extract from the new passages the SPECIFIC FACT that answers the question.
4. End your summary with a clear statement: "The answer to the question is: [specific fact]" if you can determine it from the available information.

Rules:
- Use exact names, dates, and numbers from the passages — never paraphrase proper nouns.
- For person names, use the FULL name as it appears in the passages (include middle names if stated).
- For comparison questions (X vs Y), clearly state the relevant attributes for BOTH entities and which one satisfies the question.
- For yes/no questions, state the evidence and conclude with "yes" or "no".
- If the passages do not contain the needed fact, report what IS available and state your best inference.
- Never say "cannot be determined" — always report the most relevant facts.

User: [[ ## question ## ]]
${question}

[[ ## context ## ]]
${steps.summarize_hop1.output}

[[ ## passages ## ]]
${steps.retrieve_hop2.output}

Respond with the corresponding output fields, starting with the field `[[ ## reasoning ## ]]`, then `[[ ## summary ## ]]`, and then ending with the marker for `[[ ## completed ## ]]`.
