<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You are completing the second hop of multi-hop question answering.

TASK: Combine the first-hop context with new passages to determine the answer to the question.

INSTRUCTIONS:
1. Read the new passages carefully.
2. Connect new information with what was found in the first hop.
3. Determine the answer to the original question.
4. Present your findings clearly, stating the answer.

RULES:
- Use FULL entity names exactly as written in passages (full proper names, titles, qualifiers).
- For comparison questions: state both values and which entity wins.
- For bridge questions: complete the reasoning chain to the final answer.
- Always attempt to state the answer, even if uncertain.
- Keep your response focused and under 200 words.

Your input fields are:
1. `question` (str)
2. `context` (str)
3. `passages` (str)

Your output fields are:
1. `reasoning` (str): How evidence answers the question
2. `summary` (str): Key findings with the answer clearly stated

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

User: [[ ## question ## ]]
${question}

[[ ## context ## ]]
${steps.summarize_hop1.output}

[[ ## passages ## ]]
${steps.retrieve_hop2.output}

Respond with the corresponding output fields, starting with the field `[[ ## reasoning ## ]]`, then `[[ ## summary ## ]]`, and then ending with the marker for `[[ ## completed ## ]]`.
