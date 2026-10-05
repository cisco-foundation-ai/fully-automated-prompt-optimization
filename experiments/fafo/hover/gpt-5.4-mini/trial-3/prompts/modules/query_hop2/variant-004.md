<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Output ONLY search keywords. No sentences, no markdown, no quotes, no operators. 2-4 words maximum.

User: Claim: ${claim}

Summary of first retrieval: ${steps.summarize_hop1.output}

Pick ONE proper noun from the claim that does not appear in the summary above. Output it as 2-4 search keywords. Nothing else.
