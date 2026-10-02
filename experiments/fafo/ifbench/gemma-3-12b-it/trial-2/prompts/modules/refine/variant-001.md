<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Obey every constraint in the request exactly. Produce only the requested output — no explanations, notes, or tallies.

User: Original request:
${prompt}

Previous attempt:
${steps.generate.output}

Check each constraint in the original request. If the previous attempt already satisfies all constraints, reproduce it exactly. If any constraint is violated, output a corrected version that satisfies all constraints.

Output:
