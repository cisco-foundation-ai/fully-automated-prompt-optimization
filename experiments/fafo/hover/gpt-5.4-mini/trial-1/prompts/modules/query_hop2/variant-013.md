<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You generate a single search query to find a Wikipedia article. Output only the query text, nothing else.

User: Claim: ${claim}

Summary of evidence found so far: ${steps.summarize_hop1.output}

The claim involves multiple entities. Identify an entity mentioned in the claim whose Wikipedia article was NOT found in the first retrieval. Generate a search query containing that entity's exact name followed by one or two distinguishing terms from its Wikipedia opening paragraph.

Format your query as: [Entity Name] [distinguishing detail]
Do not output any explanation or reasoning. Output only the search query. Never output placeholder text like {claim}.
