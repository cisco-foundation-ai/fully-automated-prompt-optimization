<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Output the MISSING entity name as a search query. Copy it exactly from the claim. Do not explain. Never output "N/A".

User: Claim: ${claim}

${steps.summarize_hop2.output}

Copy the MISSING entity from the line above. Output just that name as your search query.
