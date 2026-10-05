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
CLUES: [Any names, dates, details from the passages that could help locate the missing entity — alternative names, related works, associated people]
NEXT TARGET: [The exact search term to try next, informed by the CLUES above]
