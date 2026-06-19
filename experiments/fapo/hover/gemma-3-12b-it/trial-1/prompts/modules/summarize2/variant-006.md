<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You identify which entities from a claim appear in retrieved passages.

User: Claim: ${claim}

Prior findings: ${steps.summarize_hop1.output}

New passages:
${steps.retrieve_hop2_trunc.output}

Which entities or topics from the claim are now found? Which are still missing? Be brief.

NEXT SEARCH: name the most important missing entity or topic to search for next.
