<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Replace placeholders in INPUT 2 with real names from INPUT 1. Output only the restored text.

Rules:
- Replace [PERSON_N], [ORG_N], [LOCATION_N], [CODE_N], [URL_N], [NATIONALITY_N] and generic references ("the company", "the person") with correct names from INPUT 1
- Strip any preamble ("Okay,", "Sure,", "Here is", "Alright,", "Let me") from the start — begin with substantive content
- Do not add, remove, or modify any other content
- Do not refuse or add disclaimers
- Keep original language and formatting
- If INPUT 2 has hallucinated names, replace with correct ones from INPUT 1
- Every placeholder must be resolved

User: INPUT 1: ${query}

INPUT 2: ${steps.untrusted_response.output}

Output:
