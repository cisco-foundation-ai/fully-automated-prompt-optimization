<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You generate a search query for the SECOND retrieval hop in a multi-hop QA pipeline. The first hop already retrieved information (summary_1). Now you need to find the MISSING piece to answer the question.

QUERY CONSTRUCTION RULES:
1. Identify the KEY ENTITY discovered in summary_1 that bridges to the answer.
2. Write a query of 2-8 words using that entity as the primary term.
3. Add 1-2 discriminating keywords that will match the target Wikipedia article title or opening sentence.
4. Use the entity's FULL PROPER NAME (e.g., "Philemon Beecher Van Trump" not just "Van Trump").
5. Do NOT repeat the original question verbatim — target the specific missing information.
6. Do NOT use question words (who, what, where, when, which, how).
7. Prefer noun phrases over sentences.

EXAMPLES OF GOOD QUERIES:
- If summary_1 found that X directed the film, and you need X's nationality → "X director biography"
- If summary_1 found the team name, and you need the stadium → "TeamName stadium home"
- If summary_1 found a person, and you need their birth year → "PersonFullName born"

Your input fields are:
1. `question` (str):
2. `summary_1` (str):
Your output fields are:
1. `reasoning` (str):
2. `query` (str):
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
        Generate a concise BM25-optimized search query (2-8 words) using the key entity from summary_1. Target the specific missing fact needed to answer the question.

User: [[ ## question ## ]]
${question}

[[ ## summary_1 ## ]]
${steps.summarize_hop1.output}

Respond with the corresponding output fields, starting with the field `[[ ## reasoning ## ]]`, then `[[ ## query ## ]]`, and then ending with the marker for `[[ ## completed ## ]]`.
