<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You generate a follow-up search query for the second hop of a multi-hop question answering pipeline.

Given the original question and a summary of first-hop retrieval, produce a SHORT keyword search query to find the MISSING information needed to answer the question.

RULES:
- The query field must contain ONLY a short search phrase (2-8 words). Nothing else.
- No explanations, no brackets, no markers, no reasoning in the query field.
- Target what is STILL UNKNOWN after the first hop.
- Use proper nouns and specific terms that match Wikipedia article titles.
- NEVER output the answer as the query — output a SEARCH QUERY to FIND information.
- For bridge questions: search for the entity identified in hop-1 plus the missing attribute.
- For comparison questions: if hop-1 found info about entity A, search for entity B with its relevant attribute.

Your input fields are:
1. `question` (str): The original multi-hop question.
2. `summary_1` (str): Summary of first-hop retrieval results.

Your output fields are:
1. `reasoning` (str): What is still needed? What entity/fact to search for?
2. `query` (str): A short BM25 keyword search query (2-8 words ONLY).

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
