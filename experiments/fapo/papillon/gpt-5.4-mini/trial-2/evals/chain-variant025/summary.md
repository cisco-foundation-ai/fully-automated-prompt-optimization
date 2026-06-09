# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.68

## Score Breakdown
- leakage_fraction: 0.05
- privacy: 94.95
- quality: 96.40
- quality_passed: 0.96

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 2.207 | 1.253 | 7.714 |
| call_untrusted | 4.049 | 2.125 | 14.046 |
| reconstruct_response | 3.005 | 1.691 | 9.334 |
| **Total** | **9.260** | **5.487** | **23.437** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 13 |
