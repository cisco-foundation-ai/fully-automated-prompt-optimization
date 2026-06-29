---
name: spl-search
description: How to answer event-data questions (failures, errors, logins, license usage, trends) by writing SPL and running it with splunk_run_query.
---

For event-data / search questions (indexing failures, errors, skipped searches, logins, license usage, queue blockages, trends), write SPL yourself and run it with `splunk_run_query`:

- Honor the time range asked in the task via `earliest_time` / `latest_time` (e.g. "last 5 hours" → `earliest_time="-5h"`). Do not silently drop the requested window.
- Search the relevant index — operational and security events usually live in `_internal` or `_audit`.
- Do **not** use the `rest` SPL command; it is blocked server-side. Compose a normal search instead.
- Keep searches bounded and purposeful; the server caps oversized or long-running searches.

<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->