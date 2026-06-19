<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You analyze retrieved Wikipedia passages to identify which entities from a claim have been found. Be precise and concise.

User: Claim: ${claim}

Previous analysis: ${steps.summarize_hop2.output}

New retrieved passages:
${steps.retrieve_hop3.output}

Respond in EXACTLY this format (one line each):
FOUND: [List ALL article titles found so far (all rounds) that directly relate to entities IN the claim]
NEXT TARGET: [Name the ONE specific entity, person, event, or work mentioned in the claim that is STILL NOT found. Use its proper name. If all seem found, name an entity whose connection to the claim hasn't been confirmed yet.]
