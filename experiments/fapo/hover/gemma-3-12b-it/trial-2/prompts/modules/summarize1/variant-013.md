<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You are analyzing retrieved passages to verify a claim. Extract structured information about what was found.

User: Claim: ${claim}

Retrieved passages:
${steps.retrieve_hop1.output}

Respond in this exact format:
FOUND: [List the Wikipedia article titles from passages that are directly relevant to the claim]
MENTIONED: [List entity names, people, places, events mentioned in the claim that appear in the passages]
NEXT TARGET: [Name the specific entity or topic from the claim that was NOT found in these passages and needs to be searched next]
