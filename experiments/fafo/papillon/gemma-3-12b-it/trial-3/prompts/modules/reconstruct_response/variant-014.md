<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Merge two inputs into a final answer.

INPUT 1: User's original question with real names.
INPUT 2: Answer written for a redacted version (has [PERSON_1], [ORG_1] placeholders or says "the company" etc.)

Replace every placeholder and generic reference in INPUT 2 with the real name from INPUT 1. Keep everything else exactly the same.

IMPORTANT: Start immediately with the answer content. Do NOT write "Here is", "Sure", "Certainly", or any prefix. Do NOT refuse or add disclaimers.

User: INPUT 1: ${query}

INPUT 2: ${steps.untrusted_response.output}

