# Evaluation Summary

Total cases: 111

## Composite Score
- average: 93.42

## Score Breakdown
- leakage_fraction: 0.06
- privacy: 94.05
- quality: 92.79
- quality_passed: 0.93

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 2.231 | 1.104 | 6.842 |
| call_untrusted | 3.964 | 1.989 | 14.009 |
| reconstruct_response | 3.018 | 1.676 | 9.140 |
| **Total** | **9.213** | **5.038** | **28.371** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 18 |
