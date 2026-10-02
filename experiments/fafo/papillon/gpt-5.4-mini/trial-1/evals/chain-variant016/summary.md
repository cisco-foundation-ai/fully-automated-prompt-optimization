# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.04

## Score Breakdown
- leakage_fraction: 0.06
- privacy: 93.67
- quality: 96.40
- quality_passed: 0.96

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 2.483 | 1.310 | 8.839 |
| call_untrusted | 3.459 | 1.932 | 15.308 |
| reconstruct_response | 2.533 | 1.357 | 7.676 |
| **Total** | **8.475** | **4.842** | **24.599** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 15 |
