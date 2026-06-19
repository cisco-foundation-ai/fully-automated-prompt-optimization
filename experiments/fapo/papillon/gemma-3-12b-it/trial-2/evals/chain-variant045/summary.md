# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.59

## Score Breakdown
- leakage_fraction: 0.05
- privacy: 94.79
- quality: 96.40
- quality_passed: 0.96

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.713 | 1.194 | 15.980 |
| call_untrusted | 12.637 | 12.059 | 24.596 |
| reconstruct_response | 14.397 | 13.003 | 33.421 |
| **Total** | **30.747** | **27.429** | **62.379** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 13 |
