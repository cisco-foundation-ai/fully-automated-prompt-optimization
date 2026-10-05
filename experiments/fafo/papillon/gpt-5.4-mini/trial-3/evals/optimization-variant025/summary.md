# Evaluation Summary

Total cases: 111

## Composite Score
- average: 97.22

## Score Breakdown
- leakage_fraction: 0.04
- privacy: 96.25
- quality: 98.20
- quality_passed: 0.98

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 2.050 | 1.158 | 7.372 |
| call_untrusted | 3.945 | 1.923 | 14.639 |
| reconstruct_response | 2.895 | 1.469 | 9.532 |
| **Total** | **8.890** | **5.311** | **26.092** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 8 |
