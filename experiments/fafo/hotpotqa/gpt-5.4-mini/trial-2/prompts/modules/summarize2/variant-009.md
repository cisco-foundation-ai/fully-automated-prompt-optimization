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

This is the SECOND hop. Your summary is the FINAL input to the answer step.

Write a 1-3 sentence summary that contains:
1. The bridge entity identified in hop 1
2. The key fact from hop 2 passages that directly answers the question
3. For comparisons: both entities' relevant attributes

Rules:
- Be CONCISE. The answer step works better with short, focused summaries.
- Use exact names (full formal name), dates, and numbers from the passages.
- For yes/no questions, state the decisive fact and whether it confirms or denies.
- Never say "cannot be determined" — always state the most relevant available fact.
- End your summary with the sentence: "Therefore, the answer is [specific answer]."

User: [[ ## question ## ]]
${question}

[[ ## context ## ]]
${steps.summarize_hop1.output}

[[ ## passages ## ]]
${steps.retrieve_hop2.output}

Respond with the corresponding output fields, starting with the field `[[ ## reasoning ## ]]`, then `[[ ## summary ## ]]`, and then ending with the marker for `[[ ## completed ## ]]`.
