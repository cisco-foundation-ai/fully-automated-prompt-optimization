<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You are a search engine user looking up a specific Wikipedia article. Output only your search query.

User: I need to verify this claim: ${claim}

I already found these Wikipedia articles:
${steps.retrieve_hop1.output}

${steps.retrieve_hop2.output}

Summary: ${steps.summarize_hop2.output}

I'm still missing one article. The claim mentions an entity whose Wikipedia article I haven't found yet. I need to search for it by name.

My search query (just the entity name plus one identifying detail, 3-6 words total):
