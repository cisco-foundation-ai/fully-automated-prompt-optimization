<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You generate a single search query to find a Wikipedia article. Output only the query text, nothing else.

User: Claim: ${claim}

Summary of evidence found so far: ${steps.summarize_hop1.output}

The claim mentions multiple entities. One entity's Wikipedia article has NOT yet been found. Generate a search query to find that entity's article.

Your query should be the entity's exact proper name followed by one or two terms that would appear in the opening sentence of its Wikipedia article.

Do not output any explanation or reasoning. Output only the search query (3-8 words). Never output placeholder text like {claim}.
