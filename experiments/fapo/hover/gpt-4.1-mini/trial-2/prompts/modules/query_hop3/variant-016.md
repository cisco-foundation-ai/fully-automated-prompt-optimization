<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You search Wikipedia. Read the analysis below and output the MISSING entity as a search query. If MISSING says "none" or is unclear, find a proper noun from the claim not yet in any TITLES list. Must be DIFFERENT from the hop 2 query. Output 1-5 words only.

User: Claim: ${claim}

Hop 2 analysis: ${steps.summarize_hop2.output}

The hop 2 query was: ${steps.query_hop2.output}

Output the entity to search for:
