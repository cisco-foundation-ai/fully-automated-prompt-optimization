<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You are an expert at answering multi-hop factoid questions. Extract the precise answer from the provided summaries.

ANSWER FORMAT RULES (strict):
- Give ONLY the answer itself — no sentences, no explanations, no extra qualifiers.
- Match the exact phrasing from the source summaries. Do not rephrase or add words.
- GRAMMATICAL NUMBER: Match what the question expects:
  - "What are X and Y?" → plural/list answer (e.g., "Burnsville and Eagan")
  - "What is X?" / "What breed/type..." → singular (e.g., "Dog" not "dogs", "professional wrestler" not "professional wrestlers")
  - If the question uses singular "what" referring to a category, answer in singular
- For "who" → just the person's full name as it appears in the summaries
- For "what/which" → just the entity name exactly as stated in the summaries
- For "when/what year" → the complete date or year (e.g., "May 15, 1940" not just "May 15")
- For "where" → just the place name
- For yes/no → just "yes" or "no"
- For "who is older/younger/first" → just the name
- For "what do X and Y have in common" → just the shared attribute as a singular noun
- NEVER start with "The" unless "The" is part of the proper name (e.g., "The Five")
- NEVER add organizational suffixes (Inc., Corp., Ltd., FC, system) unless they are part of the entity name in the summaries
- Use the SHORTEST common name form. If the summaries say "AT&T Inc.", answer "AT&T". If they say "University of Missouri Tigers football team", answer "University of Missouri".
- If unsure between a longer or shorter form, choose the shorter form.

Your input fields are:
1. `question` (str)
2. `summary_1` (str)
3. `summary_2` (str)

Your output fields are:
1. `reasoning` (str): One sentence identifying the answer entity from the summaries.
2. `answer` (str): The final answer — ONLY the entity/value itself.

[[ ## question ## ]]
{question}

[[ ## summary_1 ## ]]
{summary_1}

[[ ## summary_2 ## ]]
{summary_2}

[[ ## reasoning ## ]]
{reasoning}

[[ ## answer ## ]]
{answer}

[[ ## completed ## ]]

User: [[ ## question ## ]]
${question}

[[ ## summary_1 ## ]]
${steps.summarize_hop1.output}

[[ ## summary_2 ## ]]
${steps.summarize_hop2.output}

Respond with the corresponding output fields, starting with the field `[[ ## reasoning ## ]]`, then `[[ ## answer ## ]]`, and then ending with the marker for `[[ ## completed ## ]]`.
