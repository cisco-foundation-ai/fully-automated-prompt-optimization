<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Generate search queries to find remaining evidence for verifying the claim. You will generate exactly 3 different queries, each targeting a different aspect of what's still unverified.

User: Claim: ${claim}

Summary of first retrieval: ${steps.summarize_hop1.output}
Summary of second retrieval: ${steps.summarize_hop2.output}

Generate exactly 3 search queries on separate lines. Each query should target a different entity or connection still needed. Format:
QUERY: <search query 1>
QUERY: <search query 2>
QUERY: <search query 3>
