<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You are helping verify a multi-hop claim by finding relevant Wikipedia articles. Summarize the retrieved passages to identify leads for finding additional articles.

User: Claim: ${claim}

Retrieved passages:
${steps.retrieve_hop1.output}

Summarize the retrieved passages. Focus on:
1. Named entities (people, places, organizations, works) mentioned in the passages
2. Connections between entities that relate to the claim
3. Leads to Wikipedia articles not yet retrieved — names, titles, or topics referenced but not directly covered by the passages above
