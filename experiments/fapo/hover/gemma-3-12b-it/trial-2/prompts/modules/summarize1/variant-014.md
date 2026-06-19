<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You analyze retrieved Wikipedia passages to identify which entities from a claim have been found. Be precise and concise.

User: Claim: ${claim}

Retrieved passages:
${steps.retrieve_hop1.output}

Respond in EXACTLY this format (one line each):
FOUND: [Only list article titles from the passages that directly relate to entities IN the claim]
NEXT TARGET: [Name the ONE specific entity, person, event, or work mentioned in the claim that was NOT found in these passages. Use its proper name.]
