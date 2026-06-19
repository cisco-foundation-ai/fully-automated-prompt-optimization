# Evaluation Summary

Total cases: 111

## Composite Score
- average: 97.30

## Score Breakdown
- leakage_fraction: 0.00
- privacy: 100.00
- quality: 94.59
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 1.758 | 0.990 | 6.357 |
| call_untrusted | 3.311 | 1.722 | 11.873 |
| reconstruct_response | 2.333 | 1.342 | 7.931 |
| **Total** | **7.402** | **4.486** | **21.295** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 6 |
