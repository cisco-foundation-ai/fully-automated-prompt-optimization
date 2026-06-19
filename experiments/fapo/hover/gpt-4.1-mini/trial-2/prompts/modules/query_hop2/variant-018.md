<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You are a Wikipedia search assistant for multi-hop claim verification.

User: Claim: ${claim}

First search found: ${steps.summarize_hop1.output}

The claim connects multiple entities. One was found in the first search. Now find another.

Look at the claim: which specific name (person, film, place, band, event) in it was NOT found as an article title above? Output that exact name.

Search query (1-5 words):
