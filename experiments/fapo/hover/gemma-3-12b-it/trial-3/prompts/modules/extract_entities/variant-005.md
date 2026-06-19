<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Extract every proper noun from the passages below. List all names of people, places, films, books, organizations, events, species, awards, and albums.

User: Claim: ${claim}

Passages:
${steps.retrieve_hop1.output}

${steps.retrieve_hop2.output}

List ALL proper nouns that appear in the passage text above. Include every person name, place name, film/book/album title, organization, species, or event mentioned anywhere in the passages. One name per line.
