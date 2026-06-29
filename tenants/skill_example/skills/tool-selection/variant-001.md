---
name: tool-selection
description: How to pick and sequence the right Splunk MCP tool for index, user, metadata, knowledge-object, and instance-health questions.
---

Route each question to the right Splunk MCP tool, and sequence multi-step calls sensibly:

- **Index questions**: list with `splunk_get_indexes`, then drill into specifics with `splunk_get_index_info`. If an index is named in the task, call `splunk_get_index_info` directly with that `index_name`. The index listing alone is NOT a sufficient basis to answer a question about a specific index's size, event count, capacity, or contents — call `splunk_get_index_info` for the relevant index(es) before answering such a question.
- **User questions**: use `splunk_get_user_list` (it already includes roles, email, and lock status for every user). Use `splunk_get_user_info` only when the question is about your own / the current account.
- **Metadata / knowledge objects**: prefer `splunk_get_metadata` for host/source/sourcetype inventories and `splunk_get_knowledge_objects` for saved searches, lookups, macros, etc.
- **Instance health / version**: use `splunk_get_info`.
- When the task asks to rank, compare, or single out a specific item (e.g. the largest / nearly-full one), do not stop after the listing step — gather the full candidate set, then drill into the specific items with their detail tool before answering. Treat the per-item detail call as mandatory, not optional.

<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->