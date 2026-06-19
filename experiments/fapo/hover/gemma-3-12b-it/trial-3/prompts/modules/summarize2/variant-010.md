<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: List which proper nouns from the claim have been found as Wikipedia article titles in the passages below. Then name the one that is STILL MISSING. Keep your answer SHORT.

User: Claim: ${claim}

First retrieval found titles:
${steps.summarize_hop1.output}

Second retrieval passages:
${steps.retrieve_hop2.output}

Output format (use exactly this):
FOUND: [title1], [title2]
MISSING: [the proper noun from the claim that still needs to be found]

Rules:
- Only list titles that MATCH proper nouns in the claim
- Always name exactly one MISSING entity
- Copy names exactly as they appear in the claim
