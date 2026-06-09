<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You generate a single search query to find a Wikipedia article. Output only the query text, nothing else.

User: Claim: ${claim}

Summary of evidence found so far: ${steps.summarize_hop1.output}

Look at the "STILL NEEDED" section above. Pick the first entity listed there and generate a search query containing that entity's exact name followed by one or two terms that would distinguish it on Wikipedia (e.g., its profession, type, or year).

Do not output any explanation or reasoning. Output only the search query. Never output placeholder text like {claim}.
