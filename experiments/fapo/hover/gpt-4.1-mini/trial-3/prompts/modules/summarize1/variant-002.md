<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You are analyzing retrieved Wikipedia passages to identify entities relevant to verifying a multi-hop claim. Your goal is to extract specific named entities (people, places, organizations, events, works) that connect the claim to its supporting evidence.

User: Claim: ${claim}

Retrieved passages:
${steps.retrieve_hop1.output}

Analyze the claim and retrieved passages. Output exactly this format:

FOUND ENTITIES: [list the specific Wikipedia article titles you found in the passages that are relevant to the claim]
KEY FACTS: [2-3 crucial facts from the passages that help verify the claim]
STILL NEEDED: [list specific entity names or Wikipedia article titles that the claim references but were NOT found in the retrieved passages — these are what we still need to search for]
