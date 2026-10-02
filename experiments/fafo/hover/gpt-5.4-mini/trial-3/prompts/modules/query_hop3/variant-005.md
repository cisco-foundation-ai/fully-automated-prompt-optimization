<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Output ONLY search keywords. No explanation, no markdown, no quotes, no boolean operators. 2-5 keywords only.

User: Claim: ${claim}

Summary of first search: ${steps.summarize_hop1.output}
Summary of second search: ${steps.summarize_hop2.output}

Two searches have run. Find an entity in the claim that NEITHER summary discusses. Focus on:
- Names mentioned in relative clauses ("who...", "which...", "that...")
- Titles of works (films, songs, albums, books)
- Events or places mentioned at the end of the claim

Copy that entity's name from the claim and add 1-2 descriptive keywords. Output 2-5 keywords total.
