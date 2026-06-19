<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You output a search query. Output ONLY the query, nothing else.

User: Claim: ${claim}

First retrieval summary: ${steps.summarize_hop1.output}

Second retrieval summary: ${steps.summarize_hop2.output}

Look at the MISSING line above. Use that entity name as your search query. If the MISSING line says "None", re-read the claim and find the entity that has no Wikipedia article retrieved yet, then output that entity's proper name.

Output ONLY the search query (the entity name, optionally with 1-2 distinguishing words). No explanation. Never output placeholder text like {claim}.
