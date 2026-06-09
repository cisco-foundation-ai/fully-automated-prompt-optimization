<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You are producing the final response to the user's query. You have two inputs:
1. The original query with full context and all identifying details.
2. A draft response that was generated from a privacy-redacted version of the query.

Instructions:
- Use the draft response as your primary source of content and structure.
- Replace any placeholders (like [PERSON], [ORG], [LOCATION], [NAME]) or generic references with the correct specific names/entities from the original query.
- If the draft response is incomplete, off-topic, or refused the request, answer the original query directly and completely using your own knowledge.
- Ensure your response fully and directly addresses what the original query asks for.
- Use the same language as the original query (if the query is in Chinese, respond in Chinese; if in Korean, respond in Korean, etc.).
- Do not mention the reconstruction process or that you are working from a draft.

User: Original query: ${query}

Draft response: ${steps.untrusted_response.output}
