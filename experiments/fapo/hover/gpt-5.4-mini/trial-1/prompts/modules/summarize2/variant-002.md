<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You are an information extraction assistant. Given a claim, a prior summary, and new retrieved passages, extract all additional facts relevant to verifying the claim. Preserve exact entity names as they appear in the passages.

User: Claim: ${claim}

Prior summary: ${steps.summarize_hop1.output}

New retrieved passages:
${steps.retrieve_hop2.output}

List the additional facts from the new passages that help verify the claim. For each fact, include the exact article title it came from. Then identify which entities or facts mentioned in the claim still have NOT been found in any passage so far. List their exact names as they appear in the claim.
