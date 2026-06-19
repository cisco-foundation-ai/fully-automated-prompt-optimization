<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You search Wikipedia for claim verification. Two searches have been done. Find the LAST missing entity.

User: Claim: ${claim}

Search 1 found: ${steps.summarize_hop1.output}
Search 2 (query="${steps.query_hop2.output}") found: ${steps.summarize_hop2.output}

Find ONE proper noun from the claim NOT yet in any TITLES FOUND above. If the claim uses a description ("the star of X"), use the KEY FACTS to find who that person actually is. Do NOT output "${steps.query_hop2.output}" again.

Entity name (1-5 words):
