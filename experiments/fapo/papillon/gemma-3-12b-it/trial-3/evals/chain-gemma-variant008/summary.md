# Evaluation Summary

Total cases: 111

## Composite Score
- average: 96.28

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 97.06
- quality: 95.50
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 4.036 | 1.319 | 19.881 |
| call_untrusted | 12.785 | 11.956 | 26.532 |
| reconstruct_response | 12.099 | 11.423 | 25.846 |
| **Total** | **28.919** | **25.269** | **58.226** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 11 |
