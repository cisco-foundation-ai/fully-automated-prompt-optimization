<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Summarize what the passages reveal about the claim. Preserve every proper noun exactly. End with one line listing all proper nouns from the claim that were NOT mentioned in any passage.

User: Claim: ${claim}

Retrieved passages:
${steps.retrieve_hop1.output}

Write a brief summary of the relevant facts from these passages. Keep all names, titles, and places exactly as written. On the last line write: "Entities not found: " followed by proper nouns from the claim that do not appear in any passage above.
