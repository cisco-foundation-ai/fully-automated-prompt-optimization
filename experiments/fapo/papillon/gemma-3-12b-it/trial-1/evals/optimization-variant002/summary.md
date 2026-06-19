# Evaluation Summary

Total cases: 111

## Composite Score
- average: 93.44

## Score Breakdown
- leakage_fraction: 0.06
- privacy: 94.08
- quality: 92.79
- quality_passed: 0.93

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.632 | 1.196 | 17.973 |
| call_untrusted | 11.263 | 10.073 | 21.905 |
| reconstruct_response | 13.692 | 12.967 | 25.971 |
| **Total** | **28.586** | **26.220** | **54.866** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 18 |
