# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.03

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 97.27
- quality: 92.79
- quality_passed: 0.93

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.807 | 1.215 | 17.500 |
| call_untrusted | 12.140 | 11.262 | 24.038 |
| reconstruct_response | 12.786 | 11.377 | 27.196 |
| **Total** | **28.733** | **25.350** | **57.673** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 13 |
