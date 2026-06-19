# Evaluation Summary

Total cases: 111

## Composite Score
- average: 96.43

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 97.36
- quality: 95.50
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 1.897 | 1.061 | 5.489 |
| call_untrusted | 3.222 | 1.891 | 13.258 |
| reconstruct_response | 2.112 | 1.297 | 6.223 |
| **Total** | **7.231** | **4.586** | **24.182** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 10 |
