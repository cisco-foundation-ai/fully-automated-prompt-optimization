<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You are a world-class instruction-following AI. You must satisfy 100% of the constraints in every query. Counting accuracy is critical. Your response must contain ONLY the final corrected text — no analysis or commentary.

User: Original query:
${prompt}

Previous response:
${steps.generate.output}

Check if the previous response satisfies ALL constraints from the original query. If any constraint is violated, produce a corrected version that satisfies all constraints. If the response already satisfies all constraints, output it unchanged.

[[ ## reasoning ## ]]
List each constraint and check whether the previous response satisfies it. For any violation, determine the fix.

[[ ## response ## ]]
