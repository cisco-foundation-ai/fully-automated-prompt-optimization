<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Generate a BM25 search query. This is the FINAL search — previous entity-name queries failed. Use CONTENT WORDS from the claim itself. Output ONLY the query, nothing else.

User: Claim: ${claim}

What we found: ${steps.summarize_hop3.output}

Previous queries (ALL FAILED):
- ${steps.query_hop2.output}
- ${steps.query_hop3.output}
- ${steps.query_hop4.output}

The missing article was NOT found by searching its name directly. Instead, extract 4-8 DISTINCTIVE CONTENT WORDS from the claim that describe what the missing entity does, where it is, or what it is associated with. These words should appear in the Wikipedia article's text even if the title doesn't match previous queries.

Output only the search query (4-8 distinctive words from the claim).
