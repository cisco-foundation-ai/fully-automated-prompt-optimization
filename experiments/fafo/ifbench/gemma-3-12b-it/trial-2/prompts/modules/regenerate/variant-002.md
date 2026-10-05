<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Obey every constraint in the request exactly. Produce only the requested output — no explanations, notes, or tallies. Verify your output satisfies every constraint before finishing.

User: Carefully follow ALL constraints in the following request:

${prompt}

Your previous attempt failed these constraints:
${failed_constraints}

Produce a new response that fixes the above failures while still obeying all other constraints in the original request.

Output:
