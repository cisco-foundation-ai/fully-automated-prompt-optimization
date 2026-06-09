<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You generate a single search query to find a Wikipedia article. Output only the query text, nothing else.

User: Claim: ${claim}

Summary of evidence found so far: ${steps.summarize_hop1.output}

The summary above identifies entities that STILL NEED to be found. Pick the most important one and generate a search query for its Wikipedia article.

Your query should be the entity's exact Wikipedia article title (3-6 words). Include disambiguation in parentheses when the entity is ambiguous: (film), (TV series), (band), (book), (album), (song).

Do not include "Wikipedia", "article", or "page" in your query. Do not search for an entity already found. Output only the search query. Never output placeholder text like {claim}.
