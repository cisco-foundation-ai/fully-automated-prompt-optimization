<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Summarize the relevant information from the retrieved passages that helps verify the claim. Preserve all proper names exactly as they appear.

User: Claim: ${claim}

Retrieved passages:
${steps.retrieve_hop1.output}

Summarize what the passages tell us about the claim. Preserve all proper names exactly as they appear.
