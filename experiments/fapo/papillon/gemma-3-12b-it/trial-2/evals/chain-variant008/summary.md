# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.08

## Score Breakdown
- leakage_fraction: 0.05
- privacy: 94.65
- quality: 95.50
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 4.050 | 1.591 | 17.438 |
| call_untrusted | 11.858 | 11.738 | 21.233 |
| reconstruct_response | 12.156 | 11.494 | 23.498 |
| **Total** | **28.064** | **25.612** | **52.848** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 12 |
