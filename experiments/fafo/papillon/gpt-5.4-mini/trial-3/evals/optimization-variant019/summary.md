# Evaluation Summary

Total cases: 111

## Composite Score
- average: 94.02

## Score Breakdown
- leakage_fraction: 0.04
- privacy: 96.16
- quality: 91.89
- quality_passed: 0.92

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 2.276 | 1.124 | 8.739 |
| call_untrusted | 3.851 | 2.029 | 16.338 |
| reconstruct_response | 2.495 | 1.509 | 6.968 |
| **Total** | **8.621** | **4.884** | **29.395** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 16 |
