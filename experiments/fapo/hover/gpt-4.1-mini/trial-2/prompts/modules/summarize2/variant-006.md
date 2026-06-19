<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You extract Wikipedia article titles from search results for multi-hop claim verification. Be precise about what is still missing.

User: Claim: ${claim}

Found in first search: ${steps.summarize_hop1.output}

New passages from second search:
${steps.retrieve_hop2.output}

Instructions: List ALL article titles found (both searches). Then carefully re-read the claim and identify any entity, person, event, or work referenced in the claim that does NOT have a matching article title yet.

ALL TITLES: [all article titles from both searches, comma-separated]
KEY FACTS: [1-2 sentences about what the new passages reveal]
MISSING ENTITY: [the exact name of one person/place/event/work from the claim that has no matching article yet — must be a proper noun that would be a Wikipedia article title]
