<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You are verifying a multi-hop claim. Summarize what entities have been found and what is still missing.

User: Claim: ${claim}

First retrieval summary:
${steps.summarize_hop1.output}

Second retrieval passages:
${steps.retrieve_hop2.output}

Identify which entities from the claim have been found across both retrievals. State clearly which entity or topic from the claim still needs to be found. Always name the missing entity — never say "all found" or "N/A".
