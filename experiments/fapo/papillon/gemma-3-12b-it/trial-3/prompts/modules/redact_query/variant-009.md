<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Replace all named entities in the query with placeholders. Output only the redacted text.

Redact these categories:
- People (names, nicknames, handles) → [PERSON_N]
- Organizations (companies, brands, schools, teams) → [ORG_N]
- Places (countries, cities, regions, buildings) → [PLACE_N]
- Nationalities/demonyms → [NATIONALITY_N]
- IDs, codes, numbers → [CODE_N]
- URLs, emails, domains → [URL_N]
- Abbreviations of any above → same placeholder

Rules:
- Over-redact: if unsure, replace it
- Single-word entities must be redacted
- Same entity = same placeholder throughout
- Keep task meaning intact
- Output redacted text only

User: ${query}
