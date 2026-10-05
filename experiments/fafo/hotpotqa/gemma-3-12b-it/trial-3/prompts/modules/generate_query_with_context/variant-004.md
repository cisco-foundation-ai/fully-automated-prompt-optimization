<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Generate a keyword search query for the second hop of a multi-hop QA pipeline. The query will be used with a BM25 search engine over Wikipedia abstracts.

Your input fields are:
1. `question` (str): The original question.
2. `summary_1` (str): Facts from the first search.

Your output fields are:
1. `reasoning` (str): What entity or fact is still needed? What keywords will find it?
2. `query` (str): A BM25 keyword query (2-5 specific words).

Key rules:
- Use the specific entity name found in hop 1 as the primary search term.
- Add 1-2 keywords that narrow to the needed fact (e.g., a person's name + "born" or "film" or "directed").
- Do NOT use natural language questions. Use keywords only.
- Do NOT include stop words (the, a, is, was, of).

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
