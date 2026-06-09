# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.35

## Score Breakdown
- leakage_fraction: 0.00
- privacy: 99.70
- quality: 90.99
- quality_passed: 0.91

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 1.790 | 1.154 | 7.010 |
| call_untrusted | 3.261 | 1.840 | 10.543 |
| reconstruct_response | 2.561 | 1.401 | 7.242 |
| **Total** | **7.612** | **4.700** | **24.001** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 11 |
