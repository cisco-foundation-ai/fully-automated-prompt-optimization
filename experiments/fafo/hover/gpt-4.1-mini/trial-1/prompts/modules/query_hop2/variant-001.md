<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Generate a search query to find additional evidence for verifying the claim.

User: Claim: ${claim}

Summary of first retrieval: ${steps.summarize_hop1.output}

Generate a focused search query to find additional supporting or refuting evidence.
