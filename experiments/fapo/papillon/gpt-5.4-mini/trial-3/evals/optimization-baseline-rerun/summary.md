# Evaluation Summary

Total cases: 111

## Composite Score
- average: 96.62

## Score Breakdown
- leakage_fraction: 0.00
- privacy: 99.55
- quality: 93.69
- quality_passed: 0.94

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 1.747 | 1.046 | 6.136 |
| call_untrusted | 2.990 | 1.672 | 9.598 |
| reconstruct_response | 2.062 | 1.362 | 6.153 |
| **Total** | **6.799** | **4.513** | **19.282** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 8 |
