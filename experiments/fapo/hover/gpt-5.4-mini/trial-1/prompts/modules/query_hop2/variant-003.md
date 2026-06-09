<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You output a Wikipedia article title to search for. Output ONLY the title, nothing else.

User: Claim: ${claim}

Summary of what has been found so far: ${steps.summarize_hop1.output}

One or more entities from the claim still need their Wikipedia article found. Pick the most important missing entity and output its Wikipedia article title exactly as it would appear on Wikipedia.

For people, use their full name. For films/shows, include disambiguation like "(2020 film)" or "(TV series)". For places, use the standard Wikipedia name.

Output ONLY the article title. No quotes, no explanation. Never output placeholder text like {claim}.
