# Evaluation Summary

Total cases: 111

## Composite Score
- average: 94.55

## Score Breakdown
- leakage_fraction: 0.04
- privacy: 96.30
- quality: 92.79
- quality_passed: 0.93

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 4.734 | 1.672 | 19.326 |
| call_untrusted | 7.071 | 3.186 | 23.174 |
| reconstruct_response | 6.760 | 3.565 | 19.619 |
| **Total** | **18.564** | **9.064** | **61.345** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 14 |
