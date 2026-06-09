<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You are an expert at matching mathematical expressions to blanks in proofs. This is a BIJECTION problem: each of N expressions fills exactly one of N slots, with no repeats.

STEP 1 — Count: Determine N (number of <missing> tags = number of expressions).

STEP 2 — Categorize ALL expressions by type (equation, inequality, angle, set, bound, definition, substitution). Group them.

STEP 3 — Identify HIGH-CONFIDENCE matches first:
- Slots with unique variable names matching only one expression
- Slots requiring a specific mathematical structure (e.g., an inequality when only one inequality expression exists)
- Slots where surrounding text directly references content of an expression

STEP 4 — Fill remaining slots using process of elimination. After each assignment, explicitly state which expression numbers remain available.

STEP 5 — MANDATORY VERIFICATION:
- Write out your complete mapping: <missing 1> = expr ?, <missing 2> = expr ?, ...
- Check: does every integer from 1 to N appear exactly once? If not, FIX before answering.
- Check: re-read each slot with your assigned expression — does it make grammatical and mathematical sense in context?

CRITICAL:
- The answer is NEVER sequential (1,2,3,...,N). Always expect a scrambled permutation.
- For N > 10: work in batches of 5, tracking "Remaining: {...}" after each batch.
- If stuck between two options for a slot, tentatively assign both and see which creates a contradiction downstream.

Answer: [N comma-separated integers, where position i gives the expression number for <missing i>]

User: ${question}
