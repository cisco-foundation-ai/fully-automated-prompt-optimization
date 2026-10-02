<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You are analyzing retrieved passages to verify a claim. Extract structured information about what was found so far across multiple retrieval rounds.

User: Claim: ${claim}

Previous analysis: ${steps.summarize_hop2.output}

New retrieved passages:
${steps.retrieve_hop3.output}

Respond in this exact format:
FOUND: [List ALL Wikipedia article titles found so far (from all rounds) that are directly relevant to the claim]
MENTIONED: [List entity names, people, places, events from the claim that have been confirmed in passages so far]
NEXT TARGET: [Name the specific entity or topic from the claim that is STILL NOT found and needs to be searched next — or "NONE" if all entities are covered]
