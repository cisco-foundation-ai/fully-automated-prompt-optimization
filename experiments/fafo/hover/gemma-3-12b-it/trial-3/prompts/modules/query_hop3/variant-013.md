<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You must output ONLY a proper noun or title from the claim that has NOT been found yet. Copy it exactly from the claim. 1-5 words only. Never output "N/A" or explain.

User: Claim: ${claim}

Found so far:
${steps.summarize_hop2.output}

TASK: Re-read the claim above. Copy the proper noun, movie title, person name, place name, or event name from the claim that is NOT mentioned in the "Found so far" section. Output ONLY that name.
