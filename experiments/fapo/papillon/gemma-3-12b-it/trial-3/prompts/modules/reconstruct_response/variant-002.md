<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You are reconstructing a complete response to a user's original query. You have access to:
1. The original query (with all identifying details intact)
2. A response that was generated from a redacted (anonymized) version of the query

Your task: Produce a final response that directly addresses the original query using the information and reasoning from the redacted response. Reintroduce the correct names, organizations, and locations from the original query where the redacted response used placeholders or generic references.

Output ONLY the final response — no preamble, explanation, or meta-commentary.

User: Original query: ${query}

Response from redacted query: ${steps.untrusted_response.output}

Produce the complete response to the original query:
