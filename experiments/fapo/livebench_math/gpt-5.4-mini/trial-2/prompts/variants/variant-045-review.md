<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You are a careful mathematics reviewer. Your job is to check a solution for errors and provide the correct final answer.

Here is the original problem:
${question}

Here is a proposed solution:
${steps.solve.output}

Review the solution above. Check the key calculations for errors. If the solution is correct, extract the final answer. If there is an error, redo the calculation correctly.

Provide your final answer in exactly one of these formats:
- Multiple choice (A-E): the letter five times on the last line (e.g., DDDDD)
- Integer answer: \boxed{N} (e.g., \boxed{127})
- Proof rearrangement: "answer:" followed by expression numbers (e.g., answer: 5, 22, 3, 17, 8)
- Exact symbolic: \boxed{expression} (e.g., \boxed{\frac{2}{7}})
