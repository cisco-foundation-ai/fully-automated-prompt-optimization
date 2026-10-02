<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You will receive a user's original query and a draft response. The draft was generated from a redacted version of the query (with names/entities removed). Produce the final, complete answer to the original query.

Your task:
- Answer the original query as helpfully and completely as possible
- Use information from the draft response where relevant
- Restore all real names, places, and entities from the original query into your response
- Where the draft uses generic placeholders or is incomplete, fill in using the original query's context and your knowledge
- Match the language of the original query
- Be thorough and detailed in your response

Output only the response.

User: Query: ${query}

Draft: ${steps.untrusted_response.output}
