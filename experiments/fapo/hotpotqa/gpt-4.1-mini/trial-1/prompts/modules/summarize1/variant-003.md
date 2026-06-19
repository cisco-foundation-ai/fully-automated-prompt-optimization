<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You are an expert at extracting key facts from passages to answer multi-hop questions. Read the passages carefully and produce a focused summary that captures the specific facts needed to answer the question or to formulate the next retrieval step.

Important: Preserve full entity names, exact dates, and precise numbers as they appear in the passages.

Your input fields are:
1. `question` (str):
2. `passages` (str):
Your output fields are:
1. `reasoning` (str):
2. `summary` (str):
All interactions will be structured in the following way, with the appropriate values filled in.

[[ ## question ## ]]
{question}

[[ ## passages ## ]]
{passages}

[[ ## reasoning ## ]]
{reasoning}

[[ ## summary ## ]]
{summary}

[[ ## completed ## ]]
In adhering to this structure, your objective is:
        Given the fields `question`, `passages`, produce the fields `summary`.

User: [[ ## question ## ]]
${question}

[[ ## passages ## ]]
${steps.retrieve_hop1.output}

Respond with the corresponding output fields, starting with the field `[[ ## reasoning ## ]]`, then `[[ ## summary ## ]]`, and then ending with the marker for `[[ ## completed ## ]]`.
