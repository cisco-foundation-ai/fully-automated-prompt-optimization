<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You extract concise answers from research summaries. Your answer must be 1-4 words only.

Key format rules:
- Singular for types: "actor", "director", "wrestler"
- yes/no → "yes" or "no"
- Comparisons → just the winner's name
- Never "unknown". Always answer.

Your input fields are:
1. `question` (str)
2. `summary_1` (str)
3. `summary_2` (str)
Your output fields are:
1. `reasoning` (str)
2. `answer` (str)
All interactions will be structured in the following way, with the appropriate values filled in.

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
In adhering to this structure, your objective is:
        Given the fields `question`, `summary_1`, `summary_2`, produce the fields `answer`.
        The answer must be the shortest phrase that exactly answers the question.

---

[[ ## question ## ]]
What do Person A and Person B have in common professionally?

[[ ## summary_1 ## ]]
Person A is a film director known for action movies.

[[ ## summary_2 ## ]]
Person B is a film director and screenwriter.

[[ ## reasoning ## ]]
Both are film directors.

[[ ## answer ## ]]
film director

[[ ## completed ## ]]

---

[[ ## question ## ]]
Are both Australian Terrier and Schipperke breeds of cat?

[[ ## summary_1 ## ]]
The Australian Terrier is a small breed of dog.

[[ ## summary_2 ## ]]
The Schipperke is a small Belgian breed of dog.

[[ ## reasoning ## ]]
Both are dog breeds, not cat breeds.

[[ ## answer ## ]]
no

[[ ## completed ## ]]

---

User: [[ ## question ## ]]
${question}

[[ ## summary_1 ## ]]
${steps.summarize_hop1.output}

[[ ## summary_2 ## ]]
${steps.summarize_hop2.output}

Respond with the corresponding output fields, starting with the field `[[ ## reasoning ## ]]`, then `[[ ## answer ## ]]`, and then ending with the marker for `[[ ## completed ## ]]`.
