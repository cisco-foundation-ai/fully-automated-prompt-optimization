<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You are helping verify a multi-hop claim by finding relevant Wikipedia articles. Summarize new passages given what was already known from prior retrieval.

User: Claim: ${claim}

Prior knowledge: ${steps.summarize_hop1.output}

New retrieved passages:
${steps.retrieve_hop2.output}

Summarize the new passages. Focus on:
1. Newly discovered named entities not mentioned in the prior knowledge
2. Facts that connect already-known entities to entities still not covered
3. Leads to the final Wikipedia article needed — names, titles, or topics that appear related to the claim but have not been directly retrieved yet
