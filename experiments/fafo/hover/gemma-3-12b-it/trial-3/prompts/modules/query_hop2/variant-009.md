<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Output the name of a person, place, or thing from the claim that was NOT found in the first retrieval. Just the name (1-4 words). Do not explain.

User: Claim: ${claim}

First retrieval found these titles:
${steps.summarize_hop1.output}

Which proper noun from the claim was NOT listed as a found title above? Output that name only.
