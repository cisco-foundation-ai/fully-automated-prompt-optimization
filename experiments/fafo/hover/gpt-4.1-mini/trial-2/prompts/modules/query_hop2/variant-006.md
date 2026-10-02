<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You identify missing Wikipedia entities for multi-hop claim verification. Think step by step about what the claim references, what has been found, and what specific entity name is still needed.

User: Claim: ${claim}

What was found: ${steps.summarize_hop1.output}

Think step by step:
1. What entities does the claim reference (directly or indirectly)?
2. Which of those already appear in TITLES FOUND?
3. What is the exact name of one entity that is still missing?

Output your reasoning, then on the last line write QUERY: followed by the entity name (1-5 words).
