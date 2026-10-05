<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Output ONLY search keywords. No explanation, no markdown, no quotes, no boolean operators. 2-6 keywords only.

User: Claim: ${claim}

Summary of first retrieval: ${steps.summarize_hop1.output}

Some parts of the claim are now verified. What part of the claim STILL LACKS evidence? Identify that part and convert it into a 2-6 keyword search query targeting the unverified entity or relationship.
