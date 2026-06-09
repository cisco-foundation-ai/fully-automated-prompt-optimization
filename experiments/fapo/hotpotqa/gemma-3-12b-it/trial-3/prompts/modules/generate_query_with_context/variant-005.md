<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Generate a search query for the second hop of a multi-hop question. The query searches Wikipedia abstracts via BM25.

Your input fields are:
1. `question` (str)
2. `summary_1` (str)

Your output fields are:
1. `reasoning` (str): What specific fact or entity is still needed?
2. `query` (str): A short search query using the entity name found in hop 1.

The query should be the NAME of the entity you want to look up (e.g., a person's name, a place, a film title). BM25 works best when you search for the exact Wikipedia article title.

All interactions will be structured in the following way, with the appropriate values filled in.

[[ ## question ## ]]
{question}

[[ ## summary_1 ## ]]
{summary_1}

[[ ## reasoning ## ]]
{reasoning}

[[ ## query ## ]]
{query}

[[ ## completed ## ]]
In adhering to this structure, your objective is:
        Given the fields `question`, `summary_1`, produce the fields `query`.

User: [[ ## question ## ]]
${question}

[[ ## summary_1 ## ]]
${steps.summarize_hop1.output}

Respond with the corresponding output fields, starting with the field `[[ ## reasoning ## ]]`, then `[[ ## query ## ]]`, and then ending with the marker for `[[ ## completed ## ]]`.
