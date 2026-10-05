<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Generate Wikipedia search queries for the FINAL missing entities. Output exactly 5 queries, one per line. Each should be a likely Wikipedia article title. No numbering, no explanations — just 5 raw queries. Never output "N/A". Try alternate name forms, disambiguations, and related titles.

User: Claim: ${claim}

First analysis: ${steps.summarize_hop1.output}
Second analysis: ${steps.summarize_hop2.output}
Third analysis: ${steps.summarize_hop3.output}

Output 5 queries targeting the STILL NEEDED entities. Use alternate phrasings, disambiguations like "(film)", "(song)", "(band)", and related entity names:
