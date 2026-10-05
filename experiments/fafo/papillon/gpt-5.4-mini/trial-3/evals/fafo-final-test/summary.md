# Evaluation Summary

Total cases: 221

## Composite Score
- average: 95.73

## Score Breakdown
- leakage_fraction: 0.01
- privacy: 99.16
- quality: 92.31
- quality_passed: 0.92

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 1.787 | 1.083 | 5.642 |
| call_untrusted | 3.284 | 1.796 | 10.859 |
| reconstruct_response | 2.306 | 1.521 | 7.102 |
| **Total** | **7.377** | **5.352** | **23.512** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 21 |
