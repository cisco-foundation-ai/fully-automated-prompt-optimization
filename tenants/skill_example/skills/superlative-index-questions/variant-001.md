---
name: superlative-index-questions
description: How to answer "which index has the most data / highest event count / is largest" superlative and ranking questions about Splunk indexes.
---

For superlative / ranking index questions ("which index has the most data / the highest event count / the largest size", "what is most of my data stored in"), follow this mandatory two-step trajectory:

1. **Step 1**: call `splunk_get_indexes` to get the candidate set.
2. **Step 2**: call `splunk_get_index_info` on the top one-to-three candidate indexes (the ones that lead by the listing's values, plus the well-known `_internal`/`_audit` if relevant) to confirm their per-index detail, THEN answer. You MUST make at least one `splunk_get_index_info` call before answering — and at most about three; do not drill into every index.

Why the drill-in is always required:
- The `splunk_get_indexes` listing is only a summary; it does NOT carry the authoritative size, the confirmed event count, or any description of what kind of data an index holds. Those come only from `splunk_get_index_info`. So you can NEVER fully answer a superlative/contents question from the listing alone — the drill-in is always required.
- This holds even when the listing shows the metric as uniform, small, or zero. A listed event count of 0 (or equal counts across indexes) does NOT mean the drill-in is pointless: you still call `splunk_get_index_info` on a candidate to confirm the count and to obtain the index's data description, then answer by naming the leading index (stating any tie) and describing its contents from the detail. The reasoning "the counts are all zero, so there is no need to check further" is explicitly wrong — always perform the drill-in call first, then answer.

**Always designate a leading item, even under a tie.** Your answer must LEAD with a specific named index — never reply that "there is none" or "all are equal so none is the highest". If the primary metric is tied (e.g. several indexes share the same size or zero event count), break the tie with a secondary signal from the detail (larger configured max size, then name order) and lead with that index, while noting the underlying values are currently equal. Then describe what that leading index contains (from its detail / its well-known role, e.g. `_internal` holds Splunk's own operational logs).

<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->