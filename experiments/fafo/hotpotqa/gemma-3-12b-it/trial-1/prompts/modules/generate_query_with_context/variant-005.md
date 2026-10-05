<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Generate a Wikipedia search query for the second retrieval hop of multi-hop question answering.

You have the original question and findings from the first hop. Your job is to generate a search query that will find ADDITIONAL information needed to answer the question correctly.

RULES:
- ALWAYS generate a real search query — never output "N/A" or say no query is needed.
- Even if you think the question is already answered, generate a VERIFICATION query to confirm or find additional supporting evidence.
- For comparison questions: if you have info about entity A, search for entity B (and vice versa).
- For bridge questions: search for the intermediate entity or the final target entity.
- Use the FULL proper name of the entity you're searching for.
- Keep the query 3-10 words, like a Wikipedia article title search.
- Think about what Wikipedia article would contain the missing or confirming information.

EXAMPLES:
- Question about "who is older, A or B?" with info about A → search for "B birth date"
- Question about "what company owns X?" with X identified → search for "X parent company"
- Question about "what film did actor Y appear in?" with Y identified → search for "Y filmography"

Your input fields are:
1. `question` (str)
2. `summary_1` (str)

Your output fields are:
1. `reasoning` (str): What additional information would help answer or verify the answer
2. `query` (str): Search query for the second hop

[[ ## question ## ]]
{question}

[[ ## summary_1 ## ]]
{summary_1}

[[ ## reasoning ## ]]
{reasoning}

[[ ## query ## ]]
{query}

[[ ## completed ## ]]

User: [[ ## question ## ]]
${question}

[[ ## summary_1 ## ]]
${steps.summarize_hop1.output}

Respond with the corresponding output fields, starting with the field `[[ ## reasoning ## ]]`, then `[[ ## query ## ]]`, and then ending with the marker for `[[ ## completed ## ]]`.
