# Evaluation Summary

Total cases: 111

## Composite Score
- average: 96.20

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 96.90
- quality: 95.50
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.627 | 1.441 | 17.603 |
| call_untrusted | 12.740 | 11.708 | 27.877 |
| reconstruct_response | 12.340 | 11.199 | 26.374 |
| **Total** | **28.708** | **26.601** | **56.733** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 12 |
