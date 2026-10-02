<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Generate a Wikipedia search query. Output ONLY the entity name to search for — nothing else.

User: Claim: ${claim}

Summary of retrievals so far: ${steps.summarize_hop3.output}

This is your last search. Which entity from the claim STILL needs its Wikipedia article? Output only the entity name:
