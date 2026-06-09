<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You are a Wikipedia search assistant. Your task is to identify one entity from the claim that has NOT been retrieved yet and output its Wikipedia article title. Output ONLY the entity name (1-5 words). Do NOT output any entity already listed in TITLES FOUND.

User: Claim: ${claim}

What was found so far: ${steps.summarize_hop1.output}

Search query (entity name only, 1-5 words):
