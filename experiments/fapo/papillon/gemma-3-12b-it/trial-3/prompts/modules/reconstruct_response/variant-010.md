<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Reconstruct the final response to the original query by combining:
1. The original query's specific details (names, places, organizations)
2. The content from the redacted response

Replace all placeholders and generic references in the redacted response with the correct entities from the original query. Keep the redacted response's structure and reasoning intact.

Do not add preamble, refuse, or ask questions. Output only the answer.

User: Original query: ${query}

Response from redacted query: ${steps.untrusted_response.output}

Final response:
