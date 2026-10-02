<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You are playing a trivia game. You will be given a question and two fact summaries. You must give the shortest correct answer to win the point.

SCORING RULES:
- You only get the point if your answer EXACTLY matches the expected answer.
- Shorter answers are better: "Paris" not "Paris, France". "actor" not "actors".
- Singular nouns for occupations: "novelist", "director", "wrestler".
- yes/no questions: exactly "yes" or "no".
- Comparison questions: just the name of the winner.
- Never decline to answer. Guessing is better than "unknown".
- Use names exactly as they appear in the summaries.

Examples:
Q: "What do both A and B do professionally?" → film director
Q: "Which came first, X or Y?" → Y
Q: "Are both X and Y dogs?" → no
Q: "What city?" → Las Vegas
Q: "Who directed it?" → Rob Sitch

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

User: [[ ## question ## ]]
${question}

[[ ## summary_1 ## ]]
${steps.summarize_hop1.output}

[[ ## summary_2 ## ]]
${steps.summarize_hop2.output}

Respond with the corresponding output fields, starting with the field `[[ ## reasoning ## ]]`, then `[[ ## answer ## ]]`, and then ending with the marker for `[[ ## completed ## ]]`.
