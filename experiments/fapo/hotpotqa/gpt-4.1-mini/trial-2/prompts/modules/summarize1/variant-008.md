<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Extract the key fact from the retrieved passages to help answer this multi-hop question.

INSTRUCTIONS:
1. Find the most relevant passage for the question.
2. QUOTE the exact sentence(s) from that passage that contain the key fact. Do not paraphrase.
3. After the quote, briefly state what additional information is still needed.

FORMAT:
- Start with: "From passage [N]: " followed by the exact quote
- Then: "Still needed: " followed by what's missing

This preserves exact entity names, dates, and phrasing from the source.

Your input fields are:
1. `question` (str)
2. `passages` (str)

Your output fields are:
1. `reasoning` (str): Which passage is relevant and why?
2. `summary` (str): Exact quote + what's still needed.

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

Respond with the corresponding output fields, starting with the field `[[ ## reasoning ## ]]`, then `[[ ## summary ## ]]`, and then ending with the marker for `[[ ## completed ## ]]`.
