# Evaluation Summary

Total cases: 111

## Composite Score
- average: 96.08

## Score Breakdown
- leakage_fraction: 0.04
- privacy: 95.75
- quality: 96.40
- quality_passed: 0.96

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.446 | 1.193 | 17.499 |
| call_untrusted | 13.589 | 10.721 | 22.142 |
| reconstruct_response | 10.850 | 10.027 | 23.342 |
| **Total** | **27.885** | **24.239** | **52.450** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 12 |
