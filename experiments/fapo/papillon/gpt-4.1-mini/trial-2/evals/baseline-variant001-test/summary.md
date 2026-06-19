# Evaluation Summary

Total cases: 221

## Composite Score
- average: 67.62

## Score Breakdown
- leakage_fraction: 0.57
- privacy: 42.93
- quality: 92.31
- quality_passed: 0.92

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 8.297 | 3.845 | 21.924 |
| call_untrusted | 6.354 | 3.767 | 19.669 |
| reconstruct_response | 6.671 | 4.063 | 20.262 |
| **Total** | **21.322** | **14.472** | **53.466** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 148 |
