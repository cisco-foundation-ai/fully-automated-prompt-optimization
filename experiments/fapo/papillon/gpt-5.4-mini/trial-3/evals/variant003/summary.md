# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.35

## Score Breakdown
- leakage_fraction: 0.01
- privacy: 98.80
- quality: 91.89
- quality_passed: 0.92

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 1.850 | 1.096 | 6.036 |
| call_untrusted | 3.345 | 1.782 | 10.793 |
| reconstruct_response | 2.243 | 1.364 | 6.584 |
| **Total** | **7.438** | **4.368** | **24.159** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 11 |
