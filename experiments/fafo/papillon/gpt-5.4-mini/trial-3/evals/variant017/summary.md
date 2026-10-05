# Evaluation Summary

Total cases: 111

## Composite Score
- average: 96.25

## Score Breakdown
- leakage_fraction: 0.00
- privacy: 99.70
- quality: 92.79
- quality_passed: 0.93

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 2.086 | 1.168 | 7.500 |
| call_untrusted | 3.275 | 1.860 | 13.700 |
| reconstruct_response | 2.006 | 1.206 | 5.598 |
| **Total** | **7.367** | **4.891** | **23.404** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 9 |
