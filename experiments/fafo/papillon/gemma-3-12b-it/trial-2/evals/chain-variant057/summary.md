# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.07

## Score Breakdown
- leakage_fraction: 0.04
- privacy: 95.54
- quality: 94.59
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 4.053 | 1.332 | 17.701 |
| call_untrusted | 12.202 | 11.807 | 23.168 |
| reconstruct_response | 12.606 | 12.471 | 22.371 |
| **Total** | **28.861** | **26.407** | **63.327** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 15 |
