# Evaluation Summary

Total cases: 442

## Composite Score
- average: 96.99

## Score Breakdown
- leakage_fraction: 0.01
- privacy: 99.19
- quality: 94.80
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 2.063 | 1.220 | 7.276 |
| call_untrusted | 3.471 | 1.896 | 12.974 |
| reconstruct_response | 2.567 | 1.489 | 8.280 |
| **Total** | **8.101** | **5.333** | **24.220** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 30 |
