<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You output a Wikipedia article title. Output ONLY the title, nothing else.

User: Claim: ${claim}

Summary of first retrieval: ${steps.summarize_hop1.output}
Summary of second retrieval: ${steps.summarize_hop2.output}

This claim involves 3 key entities that each have a Wikipedia article. Two have been found. Identify the third entity whose Wikipedia article is still missing.

Think about what entity the claim references that you have NOT seen covered in the summaries above. It might be referenced indirectly (e.g., "the director of X" → the person's name, "the city where X happened" → the city name).

Output that entity's exact Wikipedia article title. For people use their full name. For films add "(YYYY film)". For TV shows add "(TV series)". Output ONLY the title. Never output placeholder text like {claim}.
