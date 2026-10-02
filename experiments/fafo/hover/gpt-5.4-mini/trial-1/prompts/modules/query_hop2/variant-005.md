<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You generate a single search query to find a Wikipedia article. Output only the query text, nothing else.

User: Claim: ${claim}

Summary of what was found: ${steps.summarize_hop1.output}

Based on the STILL NEEDED section above, generate a search query for the first missing entity. The query should contain the entity's name followed by 1-2 distinguishing terms (profession, type, location, or year).

If there is no STILL NEEDED section, identify an entity from the claim not covered by the summary and search for it.

Do not output any explanation or reasoning. Output only the search query. Never output placeholder text like {claim}.
