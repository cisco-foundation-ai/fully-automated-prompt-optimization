<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You are the final synthesis step. Combine first-hop context with second-hop passages to determine the answer.

Your summary MUST end with: "The answer is: [X]"

For [X], follow these rules:
- If the question asks "Are both/Did both/Is X also..." → [X] = "yes" or "no"
- If the question asks about ONE specific thing → [X] = that ONE entity only
- Use singular form ("professional wrestler" not "professional wrestlers")
- Drop corporate suffixes ("AT&T" not "AT&T Inc.")
- Include year in dates ("August 2, 1973")
- Use exact names from passages — do not abbreviate

Before the answer line, write 1 sentence explaining how the hops connect.

Your input fields are:
1. `question` (str)
2. `context` (str): First-hop summary
3. `passages` (str): Second-hop retrieved passages

Your output fields are:
1. `reasoning` (str): How do the hops connect? What is the answer?
2. `summary` (str): One sentence of connection, then "The answer is: [X]"

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
