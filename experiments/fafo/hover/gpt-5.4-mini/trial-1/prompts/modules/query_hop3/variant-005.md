<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You output a Wikipedia article title to search for. Output ONLY the title, nothing else.

User: Claim: ${claim}

Articles already retrieved in hop 1:
${steps.retrieve_hop1.output}

Articles already retrieved in hop 2:
${steps.retrieve_hop2.output}

The claim mentions several entities. Most have already been found in the articles above. Identify the one entity from the claim whose Wikipedia article is NOT among those already retrieved. Output that entity's Wikipedia article title exactly as it would appear on Wikipedia.

Rules:
- For people: use full name (e.g., "John Smith")
- For films: use title with year (e.g., "Film Name (2005 film)")
- For TV shows: add "(TV series)"
- Output ONLY the title. No quotes, no explanation.
