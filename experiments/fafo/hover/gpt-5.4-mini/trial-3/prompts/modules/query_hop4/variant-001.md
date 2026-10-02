<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Output ONLY search keywords. No explanation, no markdown, no quotes, no boolean operators. 2-5 keywords only.

User: Claim: ${claim}

Summary of first search: ${steps.summarize_hop1.output}
Summary of second search: ${steps.summarize_hop2.output}
Summary of third search: ${steps.summarize_hop3.output}

This is the fourth and final search. The claim mentions entities that may not yet be covered. Look for any proper noun in the claim that has NOT appeared in any summary above. Write 2-5 search keywords for it. If all entities seem covered, search for the least-covered one.
