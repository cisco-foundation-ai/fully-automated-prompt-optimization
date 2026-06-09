<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Output exactly one proper noun to search for. Pick the entity from the claim that was NOT found as a Wikipedia article title yet. Never output "N/A" — always give a name.

User: Claim: ${claim}

Status: ${steps.summarize_hop2.output}

Copy the missing entity name from the claim. Just the name (1-4 words), nothing else.
