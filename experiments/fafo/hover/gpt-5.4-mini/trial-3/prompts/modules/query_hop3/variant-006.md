<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Output ONLY search keywords. No explanation, no markdown, no quotes, no boolean operators. 2-5 keywords only.

User: Claim: ${claim}

Summary of first search: ${steps.summarize_hop1.output}
Summary of second search: ${steps.summarize_hop2.output}

Two searches have already found information about some entities in the claim. Now identify the connecting entity — the one that LINKS the entities already found. This is often:
- An event, election, or award ceremony
- A film, album, or publication
- A geographic location or organization
Write 2-5 search keywords for this connecting entity.
