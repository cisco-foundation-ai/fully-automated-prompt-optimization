<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Output a search query (1-5 words). Find the Wikipedia article for an entity described in the claim. Do not repeat the previous query. Never output "N/A".

User: Claim: ${claim}

Previous searches found:
${steps.summarize_hop2.output}

Previous hop3 query was: ${steps.query_hop3.output}

The claim describes an entity that needs its own Wikipedia article. Try a DIFFERENT name or phrase from the claim. Just the query, nothing else.
