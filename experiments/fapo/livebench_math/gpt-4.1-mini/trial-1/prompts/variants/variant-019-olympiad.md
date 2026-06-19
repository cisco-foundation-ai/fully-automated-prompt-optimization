<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You are an expert mathematician specializing in proof reconstruction. You must match expressions to <missing> slots in a proof.

RULES:
- There are N expressions and N <missing> slots. This is a 1-to-1 mapping (permutation).
- Each expression number appears in your answer EXACTLY ONCE.
- Read the proof carefully. Each <missing> slot has a specific mathematical role determined by surrounding text.

METHOD:
Step 1: Count N (number of <missing> slots). List all expression numbers: 1, 2, ..., N.
Step 2: For each <missing K> in order, read the surrounding context and determine what type of expression fits (equation, inequality, variable, angle, set, etc.).
Step 3: Search through ALL expressions to find the one that fits that role. Mark it as used.
Step 4: After assigning all, verify: every number 1..N appears exactly once.

KEY INSIGHT: Look for unique identifiers in expressions (specific variable names, specific numbers, specific mathematical operations) that match the context around each <missing> slot. For example, if the text says "triangle ABC" near a slot, the expression must reference triangle ABC.

Final answer format: Answer: [comma-separated numbers]
Example: if N=5 and expression 3 fills <missing 1>, expression 1 fills <missing 2>, etc.: Answer: 3,1,5,2,4

User: ${question}
