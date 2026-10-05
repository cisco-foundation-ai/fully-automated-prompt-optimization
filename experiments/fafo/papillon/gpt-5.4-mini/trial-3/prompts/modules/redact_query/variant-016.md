<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Privacy redaction. Remove ALL identifying information from the query and replace each with a placeholder ([PERSON], [ORG], [LOCATION], [URL], [ID], [ENTITY]). When in doubt, always redact — over-redaction is preferred.

Redact all: personal names, organization/company/brand names, place names, nationalities/demonyms, URLs/emails/phones, IDs/passwords/credentials, product/service/app names, academic citations/authors, cultural proper nouns, and non-English proper nouns. Even famous entities must be redacted.

Preserve query structure and intent. Output only the redacted text.

User: ${query}
