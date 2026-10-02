# Evaluation Summary

Total cases: 111

## Composite Score
- average: 94.69

## Score Breakdown
- leakage_fraction: 0.05
- privacy: 94.79
- quality: 94.59
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.563 | 1.135 | 15.895 |
| call_untrusted | 12.096 | 10.146 | 24.392 |
| reconstruct_response | 11.529 | 10.698 | 23.625 |
| **Total** | **27.188** | **23.427** | **59.139** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 15 |
