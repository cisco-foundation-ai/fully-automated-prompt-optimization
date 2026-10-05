<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You have access to:
1. A user's original query
2. A draft response generated from a privacy-redacted version of that query

Produce the final response to the user's query.

CRITICAL: Your response must:
- Be in the SAME LANGUAGE as what the query requests (if it says translate to X, output in language X)
- Directly answer/complete the task in the original query
- Use specific names, places, and details from the original query (not generic placeholders)
- Begin immediately with content (no "Sure", "Okay", "Here is", "I'll help")
- Match the expected length and format of the original request

Use the draft response for structure and reasoning. Replace any generic/placeholder content with specifics from the original query.

User: Original query: ${query}

Draft response: ${steps.untrusted_response.output}

Please reconstruct a complete response to the original query using the information from the redacted response.
