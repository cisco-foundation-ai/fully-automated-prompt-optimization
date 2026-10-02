<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You generate a search query to find a Wikipedia article not yet found. Output only the query text, nothing else.

User: Claim: ${claim}

Evidence found so far: ${steps.summarize_hop1.output}

Based on the claim and evidence, identify an entity mentioned in the claim that has NOT yet been found in any article. Generate a search query that includes:
- The entity's proper name (full name for people, exact title for works)
- One or two distinguishing terms from its Wikipedia opening paragraph (e.g., profession, genre, nationality, year)

The query should be 3-8 words total. Do not output explanation or reasoning. Output only the search query. Never output placeholder text like {claim}.
