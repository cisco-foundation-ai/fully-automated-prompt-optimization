<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Reconstruct the response by replacing all placeholders with the correct entities from the original query. If the response is incomplete, supplement it to fully answer the original query. Output ONLY the final response.

User: Original query: ${query}

Redacted response: ${steps.untrusted_response.output}
