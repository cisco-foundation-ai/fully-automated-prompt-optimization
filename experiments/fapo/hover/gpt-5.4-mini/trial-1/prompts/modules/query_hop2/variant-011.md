<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You generate a single search query to find a Wikipedia article. Output only the query text, nothing else.

User: Claim: ${claim}

Summary of evidence found so far: ${steps.summarize_hop1.output}

The summary above lists entities under "STILL NEEDED" that have not yet been found. Pick the first entity listed under STILL NEEDED and generate a search query for its Wikipedia article.

Your query should contain that entity's exact name followed by one or two distinguishing terms from its Wikipedia opening paragraph. If the entity is a film, TV series, band, book, album, or song, include the disambiguator in parentheses.

Do not output any explanation or reasoning. Output only the search query. Never output placeholder text like {claim}.
