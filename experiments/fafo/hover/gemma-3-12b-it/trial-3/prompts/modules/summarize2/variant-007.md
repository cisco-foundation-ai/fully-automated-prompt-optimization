<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You are verifying a multi-hop claim by finding Wikipedia articles. List which article titles from the passages match entities in the claim, and which entity still needs its own Wikipedia article found.

User: Claim: ${claim}

First retrieval found these titles:
${steps.summarize_hop1.output}

Second retrieval passages:
${steps.retrieve_hop2.output}

Instructions:
1. List each proper noun or named entity in the claim
2. For each, state whether a Wikipedia article with that title (or very close) was found in either retrieval
3. Name the entity that still does NOT have a matching Wikipedia article title found

Always identify at least one entity as STILL MISSING. Output format:
FOUND: [entity1], [entity2]
STILL MISSING: [entity that needs its own article]
