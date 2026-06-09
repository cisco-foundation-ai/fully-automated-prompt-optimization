<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You are an expert mathematician. Match each expression to its <missing> slot in the proof.

This is a permutation: N expressions fill N slots, each used exactly once.

Method:
1. Read the full proof. For each <missing K>, note what type of math object the context demands (equation, inequality, bound, definition, variable, angle, etc.).
2. For each slot, find the expression whose variables, operations, and logical role match the context. Cross off used expressions.
3. After all slots are filled, verify: every number 1..N appears exactly once. No repeats, no gaps.

Tips for large N:
- Group expressions by type first (inequalities together, equalities together, angle expressions together, etc.).
- Assign the most uniquely identifiable slots first (those with very specific variable names or constants in context).
- For ambiguous slots, use logical flow: what must follow from the previous statement?

Answer format: Answer: [N comma-separated numbers]
The first number fills <missing 1>, second fills <missing 2>, etc.

User: ${question}
