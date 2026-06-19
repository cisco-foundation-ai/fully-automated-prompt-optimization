<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Extract the KEY BRIDGE FACT from these passages for multi-hop QA.

You are processing the FIRST HOP. Your output feeds into: (1) generating a follow-up search query, (2) the final answer step.

TASK: Find the entity/fact in the passages that BRIDGES to answering the question's second part.

RULES:
- Identify the one entity, relationship, or fact that links the question's known part to its unknown part.
- State it with the FULL PROPER NAME as it appears in passages.
- Include exactly the supporting detail needed (date, role, title, relationship).
- For COMPARISON questions ("which is older/larger?", "do both X and Y...?"): extract the specific comparable facts (dates, numbers, counts) for BOTH entities if present. State "Entity A has [value], Entity B has [value]."
- 1-2 sentences max. Be precise, not comprehensive.
- DO NOT answer the full question — identify the bridge entity/fact.

Your input fields are:
1. `question` (str)
2. `passages` (str)

Your output fields are:
1. `reasoning` (str): What's the bridge entity/fact?
2. `summary` (str): Bridge fact with full proper name (1-2 sentences).

[[ ## question ## ]]
{question}

[[ ## passages ## ]]
{passages}

[[ ## reasoning ## ]]
{reasoning}

[[ ## summary ## ]]
{summary}

[[ ## completed ## ]]

User: [[ ## question ## ]]
${question}

[[ ## passages ## ]]
${steps.retrieve_hop1.output}

You MUST respond using EXACTLY this structure:

[[ ## reasoning ## ]]
(your brief reasoning here)

[[ ## summary ## ]]
(your 1-2 sentence bridge fact here)

[[ ## completed ## ]]
