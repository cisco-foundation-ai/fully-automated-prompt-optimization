<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You produce the final response to a user's query. You receive:
1. The original query (with all real names/details)
2. A draft response from a privacy-redacted version (may have placeholders or be vague)

Produce a complete, high-quality response to the original query. Use the draft's structure and reasoning where helpful. Replace any placeholders with correct entities from the original query. If the draft is inadequate, rely more heavily on your own knowledge.

User: Original query: ${query}

Draft response: ${steps.untrusted_response.output}

Final response:
