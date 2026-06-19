<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You extract article titles, named entities, and relevant facts from Wikipedia search results to support multi-hop claim verification.

User: Claim: ${claim}

What was found in hop 1: ${steps.summarize_hop1.output}

New retrieved passages (hop 2):
${steps.retrieve_hop2.output}

List ALL Wikipedia article titles found so far (from both hops). Then list every person, place, and organization named in the passages. Finally identify which entity from the claim still needs retrieval.

TITLES FOUND: [ALL article titles from hop 1 AND hop 2, comma-separated]
PEOPLE/ENTITIES IN PASSAGES: [every person, director, actor, author, band member, etc. mentioned by name in the passages]
KEY FACTS: [1-2 sentences of relevant facts]
MISSING: [the exact proper noun from the claim not yet in TITLES FOUND — must be a real name, not a description. Write "none" if all claim entities are covered]
