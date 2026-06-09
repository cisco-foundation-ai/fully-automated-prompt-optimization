<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Redact all PII from the query below. Replace each piece of identifying information with a placeholder like [PERSON_1], [ORG_1], [LOCATION_1], [URL_1], [ID_1], etc.

Redact: names (personal, fictional, usernames), organizations (companies, brands, universities), locations (cities, countries, addresses), contact info (emails, phones, URLs, domains), and identifiers (IDs, tickers, model names).

Rules:
- Output ONLY the redacted text. Do not answer or comment on the query.
- When in doubt, redact.
- Use consistent placeholders for repeated entities.
- Apply to ALL languages and scripts.

User: ${query}
