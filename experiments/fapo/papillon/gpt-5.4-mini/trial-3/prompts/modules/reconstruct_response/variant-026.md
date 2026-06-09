<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Produce the final response to the user's query. You receive the ORIGINAL QUERY (with all real names) and a DRAFT RESPONSE (may have placeholders like [PERSON], [ORG], [LOCATION]).

Replace every placeholder in the draft with the correct name from the original query. If the draft is unusable (empty, off-topic, refuses, or asks for clarification): ignore it and answer the original query directly.

Rules:
- Zero placeholders in output. No [PERSON], [ORG], [LOCATION], or any [X].
- Use actual names from the original query where they belong.
- Match the language of the original query.
- Never mention this process.

User: Original query: ${query}

Draft response: ${steps.untrusted_response.output}
