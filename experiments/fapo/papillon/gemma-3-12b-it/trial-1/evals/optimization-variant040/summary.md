# Evaluation Summary

Total cases: 111

## Composite Score
- average: 94.87

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 96.94
- quality: 92.79
- quality_passed: 0.93

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.573 | 1.251 | 17.204 |
| call_untrusted | 11.179 | 11.214 | 19.237 |
| reconstruct_response | 11.938 | 11.105 | 23.280 |
| **Total** | **26.689** | **24.836** | **50.671** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 14 |
