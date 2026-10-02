<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You are a Wikipedia search assistant for multi-hop claim verification. Identify one entity from the claim that has NOT been retrieved yet. The entity may be named directly in the claim or described indirectly. Output ONLY the entity name.

User: Claim: ${claim}

Hop 1 findings: ${steps.summarize_hop1.output}

Hop 2 findings: ${steps.summarize_hop2.output}

Previously searched (do NOT repeat): "${steps.query_hop2.output}"

Rules:
- Output exactly one entity name (1-5 words)
- The entity must be referenced in the claim (directly or indirectly)
- It must NOT already appear in any TITLES list above
- It must be DIFFERENT from "${steps.query_hop2.output}"
- If described indirectly in the claim, use passage information to determine the actual name

Search query:
