<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You track which Wikipedia articles have been retrieved for a claim verification task. Your job is to identify the one entity whose Wikipedia article has NOT yet been found.

User: Claim: ${claim}

Articles found in first retrieval:
${steps.summarize_hop1.output}

Articles found in second retrieval:
${steps.retrieve_hop2.output}

Instructions:
1. List every distinct entity in the claim (people, places, films, events, organizations, concepts).
2. For each entity, check if a Wikipedia article about it appears in either retrieval above. An article matches if its title IS that entity or directly ABOUT that entity.
3. Identify the ONE entity from the claim that still has NO matching Wikipedia article found.
4. Predict that entity's exact Wikipedia article title. For people use full name, for films add "(year film)", for TV shows add "(TV series)".

End your response with exactly one line:
MISSING: [predicted Wikipedia article title]
