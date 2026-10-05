<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You extract Wikipedia article titles from search results for multi-hop claim verification.

User: Claim: ${claim}

Found in first search: ${steps.summarize_hop1.output}

The second search was for: "${steps.query_hop2.output}"

New passages from second search:
${steps.retrieve_hop2.output}

List ALL article titles found so far (from both searches). Then identify what the claim refers to that is NOT yet covered.

ALL TITLES: [all article titles from both searches, comma-separated]
KEY FACTS: [1-2 sentences of relevant facts from the new passages]
MISSING: [one entity/person/event from the claim not yet found as an article title, or "none"]
