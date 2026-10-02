<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You extract Wikipedia article titles from search results for multi-hop claim verification.

User: Claim: ${claim}

Retrieved passages:
${steps.retrieve_hop1.output}

List the Wikipedia article titles from the passages. Then identify what the claim refers to that is NOT yet covered.

TITLES: [article titles from passages, comma-separated]
RELEVANT FACTS: [key facts from passages about the claim]
STILL NEED: [one entity/person/event from the claim whose Wikipedia article was not retrieved]
