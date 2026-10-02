<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Output a single proper noun or entity name to search for. Copy it exactly from the claim text. Do not explain.

User: Claim: ${claim}

Titles already found:
${steps.summarize_hop1.output}

Output one proper noun from the claim that has NOT been found yet. Just the name, nothing else.
