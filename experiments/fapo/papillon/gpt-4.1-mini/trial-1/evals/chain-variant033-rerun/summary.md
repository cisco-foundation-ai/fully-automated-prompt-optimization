# Evaluation Summary

Total cases: 111

## Composite Score
- average: 94.83

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 96.87
- quality: 92.79
- quality_passed: 0.93

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 6.033 | 2.218 | 33.189 |
| call_untrusted | 7.038 | 3.641 | 20.700 |
| reconstruct_response | 7.793 | 3.630 | 27.628 |
| **Total** | **20.864** | **10.951** | **82.397** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 13 |
