<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Generate a Wikipedia search query. Output ONLY the entity name to search for — nothing else.

User: Claim: ${claim}

Summary of first retrieval: ${steps.summarize_hop1.output}

Which entity from the claim still needs its Wikipedia article? If the summary revealed someone's actual name (e.g., "the director of X" is John Smith), search for that name. Output only the entity name:
