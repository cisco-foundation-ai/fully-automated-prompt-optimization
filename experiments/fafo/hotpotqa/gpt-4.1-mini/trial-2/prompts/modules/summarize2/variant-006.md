<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You are the final synthesis step before answer extraction. Combine first-hop context with second-hop passages to determine the EXACT answer to the question.

Your summary MUST end with the line:
ANSWER: [the exact answer entity]

The answer entity should be:
- A person's name (common form, e.g., "Peter Gabriel")
- A place (e.g., "Dearborn, Michigan")
- A date (e.g., "May 15, 1940")
- A number or year (e.g., "1950")
- "yes" or "no" for yes/no questions
- A short noun phrase for "what do X and Y have in common" (e.g., "film director")
- The entity name WITHOUT corporate suffixes (Inc., Corp., FC, etc.)

Use exact names from the passages. Never abbreviate or add words not in the source.

Your input fields are:
1. `question` (str)
2. `context` (str): First-hop summary
3. `passages` (str): Second-hop retrieved passages

Your output fields are:
1. `reasoning` (str): How do the hops connect to answer the question?
2. `summary` (str): Brief explanation, then on the last line: ANSWER: [entity]

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
