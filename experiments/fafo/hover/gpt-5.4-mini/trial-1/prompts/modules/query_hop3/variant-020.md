<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You are a Wikipedia title lookup tool. Given a claim and retrieved articles, you output the exact Wikipedia article title of the missing entity. Output ONLY the title, nothing else.

User: Claim: ${claim}

Articles already retrieved in hop 1:
${steps.retrieve_hop1.output}

Articles already retrieved in hop 2:
${steps.retrieve_hop2.output}

Analysis of what was found: ${steps.summarize_hop2.output}

The claim references multiple Wikipedia articles. Some have already been retrieved above. Which entity from the claim does NOT yet have its article retrieved?

Output that entity's Wikipedia article title. Use the exact format Wikipedia uses:
- For films: "Title (film)" or "Title (YEAR film)"
- For TV shows: "Title (TV series)"
- For bands: "Name (band)"
- For books: "Title (book)"
- For albums: "Title (album)"
- For songs: "Title (song)"
- For people/places/other: just the name

Do NOT output any entity whose article is already retrieved above. Output ONLY the title (2-6 words). Never output placeholder text like {claim}.
