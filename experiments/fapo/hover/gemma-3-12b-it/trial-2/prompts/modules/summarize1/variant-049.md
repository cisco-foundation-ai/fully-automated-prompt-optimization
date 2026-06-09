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
STILL MISSING: [Name the specific entity or topic from the claim that was NOT found in these passages]
CLUES: [List at least 3 alternative approaches to find the missing entity: (1) alternative name or spelling mentioned in passages, (2) a related person/work/organization associated with the entity, (3) a descriptive phrase or category that would appear in the missing article's title]
NEXT TARGET: [The single best search term to try next — prefer alternative names from CLUES over the obvious entity name]
