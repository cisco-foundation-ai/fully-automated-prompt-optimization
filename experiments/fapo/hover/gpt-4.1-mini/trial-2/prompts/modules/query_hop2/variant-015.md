<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You search Wikipedia. Read the analysis below and output the MISSING entity as a search query. If MISSING is unclear or generic, find a better proper noun from the claim. Output 1-5 words only.

User: Claim: ${claim}

Analysis: ${steps.summarize_hop1.output}

Output the entity to search for:
