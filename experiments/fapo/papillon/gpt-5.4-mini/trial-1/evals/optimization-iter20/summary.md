# Evaluation Summary

Total cases: 111

## Composite Score
- average: 93.23

## Score Breakdown
- leakage_fraction: 0.06
- privacy: 93.67
- quality: 92.79
- quality_passed: 0.93

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 2.590 | 1.319 | 9.667 |
| call_untrusted | 3.886 | 2.122 | 16.455 |
| reconstruct_response | 2.893 | 1.526 | 9.714 |
| **Total** | **9.369** | **5.571** | **28.916** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 19 |
