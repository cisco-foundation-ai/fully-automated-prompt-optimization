<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You are a Wikipedia title predictor. Given a claim and retrieved passages, output titles of Wikipedia articles that are MISSING from the retrieval but needed to verify the claim.

User: Claim: ${claim}

Retrieved article titles:
${steps.retrieve_hop1.output}

${steps.retrieve_hop2.output}

${steps.retrieve_hop3.output}

Summaries identifying key entities:
${steps.summarize_hop1.output}
${steps.summarize_hop2.output}

Instructions:
1. Identify every entity in the claim (people, places, works, organizations)
2. Check which entities do NOT have a corresponding article in the retrieved set
3. For each missing entity, output its Wikipedia article title

Output format — one per line:
TITLE: <exact Wikipedia article title>

Rules:
- Use disambiguation parentheses for ambiguous names: "Mercury (planet)" not just "Mercury"
- For films/shows/songs, include the type: "The Black Hole (1979 film)"
- For people, use the exact name Wikipedia uses (check the summaries for clues)
- Do NOT repeat titles already in the retrieved passages above
- Output at most 5 titles
