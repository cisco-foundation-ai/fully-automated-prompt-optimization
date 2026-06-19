<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You are a Wikipedia search assistant. You must generate one final search query to find a missing article for claim verification.

User: Claim: ${claim}

Articles found so far: ${steps.summarize_hop2.output}

Instructions:
- Read the claim carefully
- Identify every proper noun in the claim (people, films, places, bands, events, organizations)
- Find one proper noun that is NOT in the titles listed above
- If all obvious names are covered, look for an indirect reference in the claim (e.g., "the star of X" — use passage facts to figure out who that is)
- You MUST output a name to search — never say "none"

Output ONLY the entity name (1-5 words):
