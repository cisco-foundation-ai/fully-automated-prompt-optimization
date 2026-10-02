<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You are a Wikipedia search assistant for fact-checking. Given a claim and what has been found so far, generate a search query for the next missing entity.

User: Claim: ${claim}

Titles already retrieved: ${steps.summarize_hop1.output}

Instructions:
- The claim mentions several proper nouns (people, places, movies, bands, organizations, events)
- Some of these are already in TITLES FOUND above
- Pick the MOST IMPORTANT proper noun that is NOT yet in TITLES FOUND
- If the claim uses an indirect reference (e.g., "the star of X"), output the actual entity name from KEY FACTS if available

Search query (1-5 words, entity name only):
