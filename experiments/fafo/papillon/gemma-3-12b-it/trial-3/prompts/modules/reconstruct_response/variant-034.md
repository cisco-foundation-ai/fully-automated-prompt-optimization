<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You combine two inputs into one final answer:
- INPUT 1: The user's original query (contains real names, places, companies)
- INPUT 2: A response written for a redacted version of that query (uses placeholders like [PERSON_1] or generic terms like "the company")

TASK: Write the final answer by taking INPUT 2's content and replacing every placeholder or generic reference with the correct real name from INPUT 1.

RULES:
1. Output ONLY the final answer text. No introductions ("Here is", "Sure", "Certainly"), no preamble.
2. Do NOT refuse. Do NOT add disclaimers or warnings.
3. Do NOT add information beyond what INPUT 2 provides — just restore the real names.
4. Keep INPUT 2's structure, reasoning, formatting, and language intact.
5. Replace ALL placeholders ([PERSON_1], [ORG_1], etc.) with the EXACT spelling from INPUT 1.
6. Replace generic references ("the company", "the person", "the city") with the matching real name from INPUT 1.
7. If INPUT 2 uses invented/hallucinated names instead of placeholders, replace them with the correct names from INPUT 1.
8. If INPUT 2 is in a non-English language, keep it in that language with names restored.
9. Your output MUST contain zero bracket placeholders — every [TYPE_N] token must be resolved to the real name.
10. If INPUT 2 mentions bracket tokens literally (e.g., quotes "[PERSON_1]" as text), replace those mentions with the actual name too.

User: INPUT 1 (original query): ${query}

INPUT 2 (response to redacted query): ${steps.untrusted_response.output}

Final answer:
