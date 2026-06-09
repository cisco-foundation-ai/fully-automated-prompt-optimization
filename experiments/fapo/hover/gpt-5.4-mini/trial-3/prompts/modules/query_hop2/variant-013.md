<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Output ONLY search keywords. No explanation, no markdown, no quotes, no boolean operators. 3-6 keywords only.

User: Claim: ${claim}

Summary of first retrieval: ${steps.summarize_hop1.output}

The claim mentions several entities. Read the claim from LEFT TO RIGHT and find the FIRST proper noun (person, place, work title, event) that is NOT discussed in the summary. Write 3-6 search keywords for that entity.
