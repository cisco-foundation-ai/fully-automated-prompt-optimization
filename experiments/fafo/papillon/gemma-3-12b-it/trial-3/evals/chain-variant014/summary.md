# Evaluation Summary

Total cases: 111

## Composite Score
- average: 96.27

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 97.03
- quality: 95.50
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 5.793 | 1.984 | 24.920 |
| call_untrusted | 6.265 | 3.391 | 18.718 |
| reconstruct_response | 5.524 | 3.119 | 16.204 |
| **Total** | **17.582** | **9.625** | **54.400** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 11 |
