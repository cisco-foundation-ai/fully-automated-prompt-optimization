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
You are performing the SECOND hop of a multi-hop question. The context contains facts from the first hop. These new passages were retrieved based on the bridge entity found in hop 1.

Your task: combine the first-hop context with these new passages to compile ALL facts needed to answer the original question.

Rules:
- State the bridge entity identified in hop 1.
- Extract the specific fact from these passages that answers the remaining part of the question.
- Use exact names, dates, numbers from the passages. Do not paraphrase proper nouns.
- If both hops together now provide enough information to answer the question, clearly state the key facts that lead to the answer.
- For comparison questions, make sure both entities' relevant attributes are clearly stated.
- Do NOT answer the question — just compile the relevant facts.
- NEVER say "cannot be determined" — always report what facts ARE available, even if incomplete.

User: [[ ## question ## ]]
${question}

[[ ## context ## ]]
${steps.summarize_hop1.output}

[[ ## passages ## ]]
${steps.retrieve_hop2.output}

Respond with the corresponding output fields, starting with the field `[[ ## reasoning ## ]]`, then `[[ ## summary ## ]]`, and then ending with the marker for `[[ ## completed ## ]]`.
