<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You analyze Wikipedia search results for multi-hop claim verification. Your main job is to track what articles have been found and what entity is STILL MISSING.

User: Claim: ${claim}

Previous findings: ${steps.summarize_hop1.output}

New passages from second search:
${steps.retrieve_hop2.output}

Instructions:
1. List ALL article titles found across both searches
2. Look at every proper noun in the claim (people, places, films, songs, events, organizations)
3. Check each one against the titles list — if ANY proper noun from the claim does not appear as a title, that is the MISSING entity
4. Only write "none" if you are CERTAIN every proper noun in the claim has a matching article title

ALL TITLES: [all article titles from both searches, comma-separated]
CLAIM ENTITIES: [list every proper noun you can identify in the claim]
STILL NEED: [one proper noun from the claim not yet in ALL TITLES — be conservative, prefer to name an entity rather than say "none"]
