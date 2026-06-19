<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You are an information extraction assistant. Extract relevant facts from new passages and identify the remaining missing entity.

User: Claim: ${claim}

Prior findings: ${steps.summarize_hop1.output}

New retrieved passages:
${steps.retrieve_hop2.output}

Extract facts from the new passages relevant to the claim. List article titles and key information found.

Then determine: the claim involves 3 Wikipedia articles. Based on ALL evidence gathered (prior findings + new passages), which entity from the claim still has NO matching article? State its exact Wikipedia article title after "MISSING:".
