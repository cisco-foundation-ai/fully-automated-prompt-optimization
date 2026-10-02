<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You generate a single search query to find a Wikipedia article. Output only the query text, nothing else.

User: Claim: ${claim}

Summary of first retrieval: ${steps.summarize_hop1.output}
Summary of second retrieval: ${steps.summarize_hop2.output}

Read the summaries carefully. Identify the entity from the claim whose Wikipedia article has NOT yet been found. Generate a search query that is the entity's exact name followed by one or two distinguishing terms that would appear in its Wikipedia opening paragraph.

Do not output any explanation or reasoning. Output only the search query. Never output placeholder text like {claim}.
