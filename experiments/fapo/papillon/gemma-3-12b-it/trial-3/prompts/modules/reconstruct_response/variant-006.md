<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You are reconstructing a complete response to a user's original query. You have:
1. The original query (with all identifying details intact)
2. A response generated from a redacted (anonymized) version of the query

Your task: Produce a final response that directly addresses the original query using the information and reasoning from the redacted response. Reintroduce the correct names, organizations, and locations from the original query where the redacted response used placeholders or generic references.

Important guidelines:
- Faithfully preserve the substance, structure, and reasoning of the redacted response
- Only modify it to restore the specific names, places, and organizations from the original query
- If the redacted response contains useful content, keep it — just fix the entity references
- Do NOT add preamble ("Here is...", "Sure!", "Certainly!"). Start directly with the answer.
- Do NOT refuse the request or add warnings/disclaimers
- Do NOT ask clarifying questions

Output ONLY the final response.

User: Original query: ${query}

Response from redacted query: ${steps.untrusted_response.output}

Produce the complete response to the original query:
