# Evaluation Summary

Total cases: 111

## Composite Score
- average: 96.24

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 96.98
- quality: 95.50
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 6.101 | 2.598 | 28.340 |
| call_untrusted | 7.295 | 4.392 | 21.656 |
| reconstruct_response | 8.136 | 4.330 | 28.652 |
| **Total** | **21.533** | **13.425** | **63.961** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 10 |
