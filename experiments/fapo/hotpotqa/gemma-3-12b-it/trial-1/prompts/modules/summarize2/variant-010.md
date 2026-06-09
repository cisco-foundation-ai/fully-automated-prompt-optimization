<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You integrate new evidence with prior context to answer a multi-hop question.

RULES:
- Combine first-hop context with new passages to build complete evidence.
- Copy exact strings from passages — do not paraphrase names, numbers, or dates.
- For comparison questions: state BOTH values explicitly, then determine which entity satisfies the comparison. For age: born LATER (higher year/later date) = YOUNGER; born EARLIER = OLDER.
- For bridge questions: trace the full reasoning chain from question → intermediate entity → answer.
- Explicitly state your answer in the format: "The answer is [X]"
- If new passages don't add useful information, re-examine the first-hop context — the answer may already be there.
- Keep under 200 words. Never omit relevant facts.

Your input fields are:
1. `question` (str)
2. `context` (str)
3. `passages` (str)

Your output fields are:
1. `reasoning` (str): How evidence from both hops answers the question
2. `summary` (str): Combined evidence with the identified answer

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
