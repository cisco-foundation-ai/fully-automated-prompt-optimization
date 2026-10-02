<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Summarize the relevant information from the second round of retrieved passages.

User: Claim: ${claim}

Prior summary: ${steps.summarize_hop1.output}

New retrieved passages:
${steps.retrieve_hop2.output}

Summarize the additional key facts relevant to verifying this claim.
