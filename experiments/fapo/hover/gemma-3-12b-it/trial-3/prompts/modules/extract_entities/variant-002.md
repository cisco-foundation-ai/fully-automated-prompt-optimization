<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Extract the 5 most relevant proper nouns from the passages below that could be Wikipedia article titles. Focus on names that relate to the claim but are NOT already passage titles.

User: Claim: ${claim}

Passages:
${steps.retrieve_hop1.output}

${steps.retrieve_hop2.output}

Output just the names, one per line. Maximum 5.
