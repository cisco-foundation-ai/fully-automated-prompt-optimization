# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.80

## Score Breakdown
- leakage_fraction: 0.04
- privacy: 96.10
- quality: 95.50
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 2.102 | 1.096 | 7.911 |
| call_untrusted | 3.390 | 1.856 | 12.621 |
| reconstruct_response | 2.630 | 1.476 | 7.704 |
| **Total** | **8.122** | **4.736** | **23.997** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 12 |
