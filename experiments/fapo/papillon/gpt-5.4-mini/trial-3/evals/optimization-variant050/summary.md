# Evaluation Summary

Total cases: 111

## Composite Score
- average: 98.20

## Score Breakdown
- leakage_fraction: 0.00
- privacy: 100.00
- quality: 96.40
- quality_passed: 0.96

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 1.656 | 1.047 | 5.066 |
| call_untrusted | 2.929 | 1.708 | 12.568 |
| reconstruct_response | 1.852 | 1.102 | 6.575 |
| **Total** | **6.437** | **4.058** | **20.830** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 4 |
