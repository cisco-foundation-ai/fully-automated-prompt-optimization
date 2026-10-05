<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Summarize what the second round of passages adds to the verification. Keep all names exactly as written.

User: Claim: ${claim}

What the first search found: ${steps.summarize_hop1.output}

New retrieved passages:
${steps.retrieve_hop2.output}

Briefly state what NEW information these passages add. Focus on proper nouns and facts not mentioned in the first search summary. Keep all names exactly as written.
