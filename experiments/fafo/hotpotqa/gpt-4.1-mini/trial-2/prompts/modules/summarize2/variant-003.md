<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You are synthesizing information from two retrieval hops to help answer a multi-hop question.

CRITICAL RULES:
- When mentioning any entity (person, place, organization, work), use the COMPLETE name exactly as it appears in the passages. Never abbreviate or shorten names.
- Quote exact phrases, titles, dates, and numbers from the passages verbatim.
- Focus on connecting information across both hops to identify the final answer entity.
- Include ALL relevant identifying information (full names with middle names, birth/death dates, titles, descriptions as stated in the passage).

Your input fields are:
1. `question` (str): The question being answered
2. `context` (str): Summary from the first retrieval hop
3. `passages` (str): Retrieved passages from the second retrieval hop

Your output fields are:
1. `reasoning` (str): How do the passages connect to the first-hop context to answer the question?
2. `summary` (str): State the key fact(s) needed to answer the question, using EXACT names and values from the passages. Include full entity descriptions as they appear in the source.

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
