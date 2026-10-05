<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Extract proper nouns from passages that could be Wikipedia article titles. Include names of people, places, films, books, bands, organizations, events, species, awards, and albums.

User: Claim: ${claim}

Passages retrieved so far:
${steps.retrieve_hop1.output}

${steps.retrieve_hop2.output}

Scan the passage text above and list every proper noun (person, place, film, book, band, organization, event, species, award, album) that appears in the passage TEXT. Include names that are only briefly mentioned. One name per line. Up to 30 names.
