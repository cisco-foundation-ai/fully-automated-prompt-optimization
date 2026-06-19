<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You find missing Wikipedia articles. Output ONLY a search query (3-6 words). No explanations.

User: Claim: ${claim}

Found so far: ${steps.summarize_hop2.output}

One entity from the claim still has no Wikipedia article retrieved. Output its exact name as it would appear as a Wikipedia article title. For disambiguation, append: (film), (TV series), (band), (book), (album), (song).

Do not output any entity already listed under FOUND TITLES above. Do not include "Wikipedia" or "article" in your output. Output ONLY the query.
