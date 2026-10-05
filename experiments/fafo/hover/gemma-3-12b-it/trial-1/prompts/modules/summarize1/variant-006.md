<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You identify which entities from a claim appear in retrieved passages.

User: Claim: ${claim}

Passages:
${steps.retrieve_hop1_trunc.output}

Which entities or topics from the claim are found in these passages? Which are still missing? Be brief.

NEXT SEARCH: name the most important missing entity or topic to search for next.
