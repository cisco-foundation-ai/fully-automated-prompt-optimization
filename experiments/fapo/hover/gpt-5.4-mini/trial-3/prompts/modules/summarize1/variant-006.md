<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Summarize the relevant information from the retrieved passages that helps verify the claim. Keep all proper names exactly as they appear in the passages.

User: Claim: ${claim}

Retrieved passages:
${steps.retrieve_hop1.output}

Write a concise summary of what these passages reveal about the claim. Include every proper name mentioned in the passages.
