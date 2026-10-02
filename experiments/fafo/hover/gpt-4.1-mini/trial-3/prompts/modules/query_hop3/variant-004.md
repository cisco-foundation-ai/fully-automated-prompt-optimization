<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Generate Wikipedia search queries. Output exactly 5 queries, one per line. Each query should be the exact or likely Wikipedia article title for an entity that still needs to be found. No numbering, no explanations, no bullets — just 5 raw queries. Never output "N/A" — always generate queries.

User: Claim: ${claim}

First analysis: ${steps.summarize_hop1.output}
Second analysis: ${steps.summarize_hop2.output}

For each entity in STILL NEEDED, output its likely Wikipedia article title. Try disambiguation variants: "(film)", "(song)", "(band)", full name vs short name. If STILL NEEDED says "None", re-read the claim and generate queries for any entity whose exact Wikipedia title might differ from how it's referenced in the claim.
