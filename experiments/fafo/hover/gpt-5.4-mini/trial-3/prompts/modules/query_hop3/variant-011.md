<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Output ONLY search keywords. No explanation, no markdown, no quotes, no boolean operators. 2-6 keywords only.

User: Claim: ${claim}

Summary of first search: ${steps.summarize_hop1.output}
Summary of second search: ${steps.summarize_hop2.output}

Extract a short phrase (2-6 words) directly from the claim that names a person, place, event, or work NOT covered in either summary. Use the exact words from the claim. Prefer phrases from the second half of the claim.
