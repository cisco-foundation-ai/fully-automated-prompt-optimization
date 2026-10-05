<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You output a Wikipedia article title to search for. Output ONLY the title, nothing else.

User: Claim: ${claim}

Summary of first retrieval: ${steps.summarize_hop1.output}
Summary of second retrieval: ${steps.summarize_hop2.output}

One entity from the claim still has no matching Wikipedia article found. Output that entity's Wikipedia article title exactly as it would appear on Wikipedia. For people, use their full name. For films/shows, use the title with disambiguation (e.g., "Film Name (2020 film)"). For places, use the standard name.

Output ONLY the article title. No quotes, no explanation. Never output placeholder text like {claim}.
