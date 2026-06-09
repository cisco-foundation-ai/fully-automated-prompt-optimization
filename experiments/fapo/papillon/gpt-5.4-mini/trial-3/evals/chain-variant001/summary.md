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
| redact_query | 1.962 | 1.159 | 7.787 |
| call_untrusted | 3.160 | 1.899 | 9.927 |
| reconstruct_response | 2.424 | 1.531 | 7.066 |
| **Total** | **7.546** | **4.968** | **23.172** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 11 |
