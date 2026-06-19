<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You are reconstructing a response by combining the original query context with a response generated from a redacted version of the query.

Your task: produce a complete, helpful response that addresses the original query directly.

Instructions:
1. The original query is your primary reference for WHAT the user wants. Follow its instructions exactly.
2. The redacted response provides useful structure and content. Use it as a starting point.
3. If the original query requests output in a specific language (e.g., "translate to Chinese", "traduci in italiano", "翻译成中文"), your output MUST be in that target language.
4. Replace any placeholder references or generic terms with the specific entities from the original query.
5. Ensure your response fully addresses the scope and detail level implied by the original query.
6. Do not include any preamble, meta-commentary, or acknowledgment. Start directly with the response content.

User: Original query: ${query}

Response from redacted query: ${steps.untrusted_response.output}

Please reconstruct a complete response to the original query using the information from the redacted response.
