<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Output ONLY search keywords. No explanation, no markdown, no quotes, no boolean operators. 2-5 keywords only.

User: Claim: ${claim}

Summary of first retrieval: ${steps.summarize_hop1.output}

The first search found information about the main topic. Now search for a DIFFERENT entity from the claim — pick a proper noun (person, place, work, event) that appears in the claim but was NOT the focus of the summary above. Write 2-5 search keywords.
