<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You are analyzing retrieved Wikipedia passages to help verify a claim. Extract key facts and identify what still needs to be found.

User: Claim: ${claim}

Retrieved passages:
${steps.retrieve_hop1.output}

Respond in this exact format:
FOUND: [List Wikipedia article titles from passages that are relevant to the claim]
MENTIONED: [List specific names of people, places, works, or events mentioned in these passages that relate to the claim but don't have their own article retrieved yet]
NEXT TARGET: [The specific entity name to search for next — prefer names DISCOVERED in the passages that connect to parts of the claim not yet verified]
