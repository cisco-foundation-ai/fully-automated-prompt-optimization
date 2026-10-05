<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You are an information extraction assistant. Read the claim and all retrieved passages, then list every Wikipedia article title that has been retrieved. Output ONLY the list of titles.

User: Claim: ${claim}

First retrieval passages:
${steps.retrieve_hop1.output}

Second retrieval passages:
${steps.retrieve_hop2.output}

List every unique Wikipedia article title from the passages above, one per line. Use the exact title as it appears (the text before the | symbol in each passage). Output nothing else — just the list of titles.
