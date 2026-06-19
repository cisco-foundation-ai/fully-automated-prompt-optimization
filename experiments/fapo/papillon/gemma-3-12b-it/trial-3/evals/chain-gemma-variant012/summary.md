# Evaluation Summary

Total cases: 111

## Composite Score
- average: 96.76

## Score Breakdown
- leakage_fraction: 0.04
- privacy: 96.22
- quality: 97.30
- quality_passed: 0.97

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 5.067 | 1.379 | 17.257 |
| call_untrusted | 12.003 | 12.159 | 26.912 |
| reconstruct_response | 11.453 | 11.511 | 20.902 |
| **Total** | **28.523** | **25.798** | **58.416** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 10 |
