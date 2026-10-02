<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You generate Wikipedia search queries. Read the analysis below and output ONLY the entity listed under "NOT YET RETRIEVED". Output the exact entity name, nothing else. 1-5 words only.

User: Claim: ${claim}

Analysis from hop 1: ${steps.summarize_hop1.output}
Analysis from hop 2: ${steps.summarize_hop2.output}

Output the entity from "NOT YET RETRIEVED" as your search query (1-5 words only):
