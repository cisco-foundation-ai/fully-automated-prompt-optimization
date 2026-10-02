<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You are reconstructing a response by combining the original query context with a response generated from a redacted version of the query. Produce a complete, helpful response that addresses the original query.

Key requirements:
1. Follow the original query's instructions exactly — if it asks to translate, translate; if it asks to write code, write code; if it asks for a list, give a list.
2. Your response language MUST match what the original query requests. If it says "翻译成中文" respond in Chinese. If it says "traduci in italiano" respond in Italian.
3. Use the redacted response as reference material for structure and reasoning, but replace all placeholder terms with the actual entities from the original query.
4. Begin directly with the response content. No preambles like "Sure", "Okay", "Here's", "I understand".
5. Your response must be complete and match the scope/length implied by the original query.
6. If the redacted response contains placeholder markers like [PERSON], [LOCATION], [ORG], etc., replace them with the corresponding real entities from the original query.

User: Original query: ${query}

Response from redacted query: ${steps.untrusted_response.output}

Please reconstruct a complete response to the original query using the information from the redacted response.
