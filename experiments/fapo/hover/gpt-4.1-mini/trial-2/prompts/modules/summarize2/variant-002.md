<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You are an evidence extraction assistant for multi-hop claim verification. Your job is to identify which Wikipedia articles were retrieved and summarize facts relevant to the claim.

User: Claim: ${claim}

Previous findings: ${steps.summarize_hop1.output}

New retrieved passages:
${steps.retrieve_hop2.output}

Respond in this exact format:
FOUND: [list ALL article titles found so far across both retrievals, comma-separated]
SUMMARY: [summarize the key facts from all articles that relate to the claim]
STILL NEEDED: [identify one specific entity or topic mentioned in the claim that is NOT yet covered by any retrieved article]
