<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Generate a Wikipedia search query. Output ONLY the entity name to search for — nothing else.

User: Claim: ${claim}

Summary of retrievals so far: ${steps.summarize_hop2.output}

Which entity from the claim still needs its Wikipedia article? Look at what's marked NOT FOUND or STILL MISSING. If a proper name was resolved from an indirect reference, use that name. Output only the entity name:
