<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You extract Wikipedia article titles from retrieved passages to track which entities have been found for claim verification.

The retrieved passages use this format: [N] «Title | passage text»
Each passage starts with its Wikipedia article title before the pipe character.

User: Claim: ${claim}

Retrieved passages:
${steps.retrieve_hop1.output}

Instructions:
1. Read the claim carefully and identify ALL named entities it mentions or implies (people, places, films, songs, events, organizations, etc.)
2. Check which of those entities appear as article titles in the retrieved passages
3. Output in this exact format:

CLAIM ENTITIES: [list every named entity mentioned or implied in the claim]
FOUND TITLES: [list the exact Wikipedia article titles from the passages that match claim entities]
STILL NEEDED: [list the specific entity names from the claim that do NOT have a matching passage title — these must be searched for next]
