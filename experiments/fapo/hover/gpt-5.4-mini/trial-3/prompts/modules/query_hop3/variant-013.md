<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Output ONLY search keywords. No explanation, no markdown, no quotes, no boolean operators. 3-6 keywords only.

User: Claim: ${claim}

Summary of first search: ${steps.summarize_hop1.output}
Summary of second search: ${steps.summarize_hop2.output}

Read the claim from RIGHT TO LEFT (starting at the end). Find the LAST proper noun (person, place, work title, event) mentioned in the claim that is NOT discussed in either summary. Write 3-6 search keywords for it.
