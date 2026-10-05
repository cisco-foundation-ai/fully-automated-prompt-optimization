# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.80

## Score Breakdown
- leakage_fraction: 0.00
- privacy: 99.70
- quality: 91.89
- quality_passed: 0.92

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 2.033 | 1.051 | 7.409 |
| call_untrusted | 3.457 | 1.740 | 12.263 |
| reconstruct_response | 2.313 | 1.324 | 8.154 |
| **Total** | **7.802** | **4.518** | **25.546** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 10 |
