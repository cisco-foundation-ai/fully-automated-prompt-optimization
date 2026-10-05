<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Generate a short BM25 search query to find a Wikipedia article. Output ONLY the query (3-8 words), nothing else.

User: Claim: ${claim}

Analysis: ${steps.summarize_hop3.output}

Previous failed queries:
- ${steps.query_hop2.output}
- ${steps.query_hop3.output}

Look at NEXT TARGET above. Both previous queries failed. Try a COMPLETELY different approach:
- If target is a person: try their role/occupation + associated work
- If target is a work: try creator name + work type
- If target is an event: try year + location + type
