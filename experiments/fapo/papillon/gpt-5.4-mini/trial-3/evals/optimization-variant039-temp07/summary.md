# Evaluation Summary

Total cases: 111

## Composite Score
- average: 98.05

## Score Breakdown
- leakage_fraction: 0.00
- privacy: 99.70
- quality: 96.40
- quality_passed: 0.96

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 2.181 | 1.364 | 7.958 |
| call_untrusted | 3.593 | 1.993 | 12.321 |
| reconstruct_response | 2.441 | 1.574 | 7.033 |
| **Total** | **8.215** | **5.381** | **23.169** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 5 |
