<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Output the name of the entity from the claim that is still missing. Just the name (1-4 words). Never output "N/A".

User: Claim: ${claim}

${steps.summarize_hop2.output}

Copy the missing entity name exactly as it appears in the claim. Output just that name, nothing else.
