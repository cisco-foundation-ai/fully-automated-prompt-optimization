<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Pick ONE name from the list below that you have NOT tried yet. Output just that name.

User: Names found in passages:
${steps.extract_entities.output}

Already tried:
1. ${steps.query_hop3.output}
2. ${steps.query_hop3b.output}

Pick a different name from the list. Just the name, nothing else.
