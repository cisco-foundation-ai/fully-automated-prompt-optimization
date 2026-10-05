<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You search Wikipedia. Find the ONE proper noun from the claim that is missing from the titles below.

User: Claim: ${claim}

Titles found: ${steps.summarize_hop2.output}

Previous query: ${steps.query_hop2.output}

Which proper noun from the claim is NOT in the titles above? Do NOT repeat the previous query. Output that name only (1-5 words):
