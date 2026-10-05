<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Produce the final response to the original query below. You have a draft response generated from a redacted version of the query — use it as your starting point, but replace placeholders with the real names from the original query. If the draft is unhelpful or refuses the request, answer the query yourself. Output only the response.

User: Original query: ${query}

Draft response: ${steps.untrusted_response.output}
