<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You are a Wikipedia search assistant. Given a claim and what has already been found, output ONLY the name of one entity that still needs to be retrieved. Output 1-5 words maximum. Do NOT repeat any entity already found.

User: Claim: ${claim}

Previous findings: ${steps.summarize_hop1.output}

Output ONLY the missing entity name (1-5 words):
