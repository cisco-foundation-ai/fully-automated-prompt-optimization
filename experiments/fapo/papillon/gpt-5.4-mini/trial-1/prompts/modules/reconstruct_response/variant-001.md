<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You are reconstructing a response by combining the original query context with a response generated from a redacted version of the query. Produce a complete, helpful response that addresses the original query.

User: Original query: ${query}

Response from redacted query: ${steps.untrusted_response.output}

Please reconstruct a complete response to the original query using the information from the redacted response.
