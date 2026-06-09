# Evaluation Summary

Total cases: 111

## Composite Score
- average: 96.02

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 97.45
- quality: 94.59
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 2.230 | 1.100 | 8.771 |
| call_untrusted | 3.589 | 2.205 | 11.404 |
| reconstruct_response | 2.555 | 1.389 | 7.935 |
| **Total** | **8.375** | **5.028** | **26.934** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 10 |
