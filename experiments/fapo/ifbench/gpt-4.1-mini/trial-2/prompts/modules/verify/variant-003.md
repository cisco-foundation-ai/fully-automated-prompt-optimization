<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You receive a query with constraints and a response. Check if the response satisfies all constraints. If it does, output it EXACTLY as-is with zero changes. If it has clear violations you can fix, output a minimally corrected version. When in doubt, output the original unchanged.

IMPORTANT: Your output will be scored. Prefer outputting the original response unchanged over making risky edits that might break other constraints.

User: Query: ${prompt}

Response: ${steps.generate.output}

Output the response (unchanged if correct, or with minimal fixes):
