# Evaluation Summary

Total cases: 111

## Composite Score
- average: 96.77

## Score Breakdown
- leakage_fraction: 0.02
- privacy: 98.05
- quality: 95.50
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 1.935 | 1.228 | 5.947 |
| call_untrusted | 3.504 | 1.882 | 12.130 |
| reconstruct_response | 2.590 | 1.495 | 8.186 |
| **Total** | **8.029** | **5.033** | **22.450** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 9 |
