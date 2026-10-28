<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

# Synthetic Example Requirements

Requirements for pruning noncompliant synthetic examples under a tenant's
synthetic examples root, such as `tenants/<tenant_id>/datasets/synthetic_artifacts/`.

## Structure and realism

- Each synthetic message should mirror a realistic email structure: subject,
  greeting, and signature.
- Use credible phishing TTPs and believable tenant or partner references when
  appropriate.
- Avoid implausible or random strings that break realism.
- Missing-body examples are allowed when intentionally used as hard cases.

## File structure

Each example directory should include:

- `Prompt.pdf.txt`
- `Context - Tools.pdf.txt`
- `Context - Stealth Watch.pdf.txt`
- `Context - Email Body.pdf.txt` or `Context - No Email Body.pdf.txt`
- `Summary.pdf.txt`

## Labels and hashes

- Keep `labels_review.csv` and `hard_labels_review.csv` aligned with
  `Summary.pdf.txt` and the existing example directories.
- `attachments_sha256` values must be realistic 64-hex values, not
  placeholders such as strings of all `A`, all `B`, or all `0`.
