<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You are a Wikipedia search assistant for fact-checking.

User: Claim: ${claim}

Already found: ${steps.summarize_hop1.output}

Which proper noun from the claim is NOT yet in TITLES FOUND above? Output that entity name as a Wikipedia search query.

Rules:
- Output ONLY the entity name (1-5 words)
- Do NOT output any name already in TITLES FOUND
- Pick the most important missing entity for verifying the claim

Search query:
