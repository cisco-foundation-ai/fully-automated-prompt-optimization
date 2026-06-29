---
name: answer-formatting
description: How to format final answers — be decisive, exhaustive on lists, direct on yes/no, and match the requested structure.
---

Format the final answer (after the `Answer:` marker) to fully and decisively resolve the task:

- **Never give up or punt.** Always produce the best possible direct answer from the tool results you obtained. Do not refuse, do not say you "cannot determine" the answer, and do not ask the user what to do next. Once you have run the appropriate tools, you have enough to answer.
- **Report the data as the server reports it.** If sizes, event counts, or other metrics come back small, uniform, or zero, that is the real current state — report it plainly and still answer. Do not editorialize that the data is "unusable", a "placeholder", or a "configuration issue"; just answer using the values returned.
- **Be exhaustive for list / inventory questions.** When asked to list "all" of something, present the complete set returned by the tool — do not show only "a few" or a sample. When the listing tool already returns the full set (users, saved searches, sourcetypes, the index list), report every item from that single response; you do NOT need a separate per-item call for each one. Summarize compactly so the full set fits in the answer.
- **Be direct on yes/no questions.** Lead with a clear Yes or No grounded in the data, then give the supporting detail. For a conditional follow-up ("...and if so, which?"), answer both parts explicitly, including stating that none were found when that is the case. Avoid hedging words like "likely" or "might" when the evidence is already in the tool output.
- **Match the requested structure.** When the task names or implies distinct parts (e.g. two named items to compare, or two phenomena to report), give each part its own `##` Markdown section heading using the wording from the task, so every requested part is clearly and separately covered.

<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->