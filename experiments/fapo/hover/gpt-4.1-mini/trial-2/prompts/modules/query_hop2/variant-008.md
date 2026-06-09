<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You search Wikipedia for claim verification. Look at the proper nouns in the claim. Find one that does NOT appear in the titles already retrieved. Output ONLY that name.

User: Claim: ${claim}

Already retrieved: ${steps.summarize_hop1.output}

Look at the claim text. Find a proper noun (person name, film title, band name, place, event) in the claim that is NOT in TITLES FOUND above. Output that exact name only (1-5 words):
