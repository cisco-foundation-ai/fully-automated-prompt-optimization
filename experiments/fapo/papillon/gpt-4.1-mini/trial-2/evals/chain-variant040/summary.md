# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.45

## Score Breakdown
- leakage_fraction: 0.04
- privacy: 96.30
- quality: 94.59
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 5.835 | 2.293 | 24.561 |
| call_untrusted | 7.029 | 3.667 | 26.285 |
| reconstruct_response | 8.873 | 3.892 | 35.344 |
| **Total** | **21.737** | **10.819** | **65.899** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 13 |
