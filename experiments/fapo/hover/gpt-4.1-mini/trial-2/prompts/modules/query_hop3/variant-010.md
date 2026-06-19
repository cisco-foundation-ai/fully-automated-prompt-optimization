<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You search Wikipedia for claim verification. Look at the proper nouns in the claim. Find one that does NOT appear in any titles already retrieved across both hops. Output ONLY that name.

User: Claim: ${claim}

Hop 1 results: ${steps.summarize_hop1.output}
Hop 2 results: ${steps.summarize_hop2.output}

Look at the claim text. Find a proper noun (person name, film title, band name, place, event) in the claim that has NOT been retrieved in either hop. Output that exact name only (1-5 words):
