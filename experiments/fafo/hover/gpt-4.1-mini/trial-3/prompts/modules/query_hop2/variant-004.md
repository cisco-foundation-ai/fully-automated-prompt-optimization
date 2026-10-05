<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Generate Wikipedia search queries. Output exactly 5 queries, one per line. Each query should be the exact or likely Wikipedia article title for an entity that needs to be found. No numbering, no explanations, no bullets — just 5 raw queries.

User: Claim: ${claim}

Analysis: ${steps.summarize_hop1.output}

For each entity in STILL NEEDED, output its likely Wikipedia article title. If fewer than 5 entities are needed, add alternate title phrasings (with/without disambiguation like "(film)", "(band)", "(song)").
