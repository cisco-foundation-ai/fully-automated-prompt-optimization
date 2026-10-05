<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You extract Wikipedia article titles from retrieved passages to track which entities have been found for claim verification.

The retrieved passages use this format: [N] «Title | passage text»
Each passage starts with its Wikipedia article title before the pipe character.

User: Claim: ${claim}

Prior analysis: ${steps.summarize_hop1.output}

New retrieved passages:
${steps.retrieve_hop2.output}

Instructions:
1. Check the STILL NEEDED entities from the prior analysis
2. Look for those entities in the new retrieved passages (match by article title)
3. Output in this exact format:

FOUND TITLES: [list ALL Wikipedia article titles found across BOTH rounds that match claim entities]
STILL NEEDED: [list any claim entities that still have NOT been found in any passage title — write "None" only if every claim entity has been found]
