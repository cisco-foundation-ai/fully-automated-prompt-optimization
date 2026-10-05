# Evaluation Summary

Total cases: 221

## Composite Score
- average: 84.90

## Score Breakdown
- leakage_fraction: 0.23
- privacy: 77.49
- quality: 92.31
- quality_passed: 0.92

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 4.412 | 1.825 | 10.603 |
| call_untrusted | 4.285 | 2.225 | 15.996 |
| reconstruct_response | 3.388 | 1.924 | 11.846 |
| **Total** | **12.085** | **7.377** | **33.946** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 74 |
