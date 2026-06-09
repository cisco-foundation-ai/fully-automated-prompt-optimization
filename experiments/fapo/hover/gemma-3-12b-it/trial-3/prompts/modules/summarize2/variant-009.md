<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Output the proper noun from the claim that has NOT appeared as a Wikipedia article title in any retrieval so far. Just the name (1-4 words). Never say "all found".

User: Claim: ${claim}

Titles found so far:
${steps.summarize_hop1.output}

Second retrieval passages:
${steps.retrieve_hop2.output}

Which proper noun from the claim is still missing? Output just that name.
