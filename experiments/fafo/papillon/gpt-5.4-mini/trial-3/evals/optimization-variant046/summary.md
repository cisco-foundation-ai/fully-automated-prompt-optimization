# Evaluation Summary

Total cases: 111

## Composite Score
- average: 96.70

## Score Breakdown
- leakage_fraction: 0.00
- privacy: 99.70
- quality: 93.69
- quality_passed: 0.94

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 1.807 | 1.149 | 5.384 |
| call_untrusted | 2.938 | 1.608 | 9.808 |
| reconstruct_response | 2.232 | 1.370 | 6.674 |
| **Total** | **6.977** | **4.575** | **17.769** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 8 |
