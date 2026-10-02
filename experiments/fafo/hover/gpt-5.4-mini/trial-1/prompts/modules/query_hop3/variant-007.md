<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You output a single Wikipedia article title. Output ONLY the title, nothing else.

User: Claim: ${claim}

What I already found about this claim:
${steps.summarize_hop1.output}

${steps.summarize_hop2.output}

This is a 3-hop claim requiring 3 Wikipedia articles. Two have already been found. What is the third? Read the claim carefully — it mentions or implies a third entity (person, place, film, event, organization) whose article is still missing.

Output that entity's Wikipedia article title. Use the entity's proper name exactly as Wikipedia would title it. Nothing else.
