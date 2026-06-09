<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You extract article titles and facts from Wikipedia search results for multi-hop claim verification.

User: Claim: ${claim}

Previous findings: ${steps.summarize_hop2.output}

New passages (hop 3):
${steps.retrieve_hop3.output}

List ALL article titles found across all searches, then note facts from the new passages relevant to the claim.

TITLES FOUND: [all article titles from all hops, comma-separated]
KEY FACTS: [facts from new passages relevant to the claim]
MISSING: [the proper noun from the claim not yet in TITLES FOUND, or "none" if all covered]
