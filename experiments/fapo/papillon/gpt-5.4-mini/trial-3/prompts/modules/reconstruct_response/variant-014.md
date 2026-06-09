<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You are producing the final response to the user's query. You have two inputs:
1. The original query with full context.
2. A draft response that was generated from a privacy-redacted version of the query.

Instructions:
- Use the draft response as your primary source of content and structure.
- CRITICAL: Replace every placeholder ([PERSON], [ORG], [LOCATION], [URL], [ID], [ENTITY]) with the exact corresponding name or entity from the original query. Never use generic terms like "the person", "the company", "the user" when the original query contains the actual name.
- If the original query itself contains anonymization markers (like <PRESIDIO_ANONYMIZED_PERSON>, [Client's Name], or similar), preserve those markers exactly as they appear in the original.
- If the draft response is incomplete, off-topic, or refused the request, answer the original query directly and completely using your own knowledge.
- Ensure your response fully addresses what the original query asks for.
- Use the same language as the original query.
- Do not mention the reconstruction process or that you are working from a draft.

User: Original query: ${query}

Draft response: ${steps.untrusted_response.output}
