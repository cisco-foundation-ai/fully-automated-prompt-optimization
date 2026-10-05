<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You are reconstructing a response. You receive:
1. The user's ORIGINAL query (with all specific details)
2. A TEMPLATE response (generated from a privacy-redacted version of the query)

Instructions:
- Treat the template response as a scaffold. Fill in all placeholder references ([PERSON], [LOCATION], [ORG], etc.) with the actual entities from the original query.
- If the original query is in one language but asks for output in another (e.g., "translate to Chinese", "traduci in italiano"), your output MUST be in the requested target language.
- If the template response is generic or off-topic, ignore it and respond directly to the original query instead.
- Never include preambles ("Sure", "Okay", "Here's"). Start with the actual content.
- Your output should be a complete, direct response to the original query.

User: Original query: ${query}

Template response: ${steps.untrusted_response.output}

Please reconstruct a complete response to the original query using the information from the redacted response.
