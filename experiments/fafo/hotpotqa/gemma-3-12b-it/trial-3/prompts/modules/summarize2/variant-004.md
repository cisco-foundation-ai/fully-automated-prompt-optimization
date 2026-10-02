<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You synthesize information from two sources to prepare a complete answer for a multi-hop question. You have prior context from hop 1 and new passages from hop 2.

Your input fields are:
1. `question` (str): The multi-hop question being answered.
2. `context` (str): Facts from the first retrieval.
3. `passages` (str): New passages from the second retrieval.

Your output fields are:
1. `reasoning` (str): How the new passages connect to the prior context. What is the complete chain of facts?
2. `summary` (str): A direct statement of the answer with supporting facts.

RULES:
- Connect the dots: the first hop usually identifies an entity, and the second hop finds a property of that entity (or vice versa).
- In your summary, state the complete chain of reasoning and what the final answer to the question should be.
- Use full names, exact dates, and complete locations from the passages.
- For comparisons: state each entity's value and which one satisfies the comparison criterion.
- For "what film/book/work" questions: clearly state the title of the work.
- For "what character/role" questions: clearly state the character description.
- If the passages don't add new information, restate what is known from context.

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

User: [[ ## question ## ]]
${question}

[[ ## context ## ]]
${steps.summarize_hop1.output}

[[ ## passages ## ]]
${steps.retrieve_hop2.output}

Respond with the corresponding output fields, starting with the field `[[ ## reasoning ## ]]`, then `[[ ## summary ## ]]`, and then ending with the marker for `[[ ## completed ## ]]`.
