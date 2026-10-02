<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Output ONLY search keywords. No explanation, no markdown, no quotes, no boolean operators. 2-5 keywords only.

User: Claim: ${claim}

Summary of first search: ${steps.summarize_hop1.output}
Summary of second search: ${steps.summarize_hop2.output}

Two searches have already run. Find the remaining proper noun in the claim that has received the LEAST coverage in the summaries above. It might be a place, a date-related event, a lesser-known person, or a specific work title. Write 2-5 search keywords for it.
