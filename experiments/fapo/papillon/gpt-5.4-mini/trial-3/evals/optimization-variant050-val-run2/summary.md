# Evaluation Summary

Total cases: 111

## Composite Score
- average: 96.55

## Score Breakdown
- leakage_fraction: 0.01
- privacy: 99.40
- quality: 93.69
- quality_passed: 0.94

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 1.673 | 1.013 | 5.572 |
| call_untrusted | 2.756 | 1.450 | 10.265 |
| reconstruct_response | 1.868 | 1.056 | 5.779 |
| **Total** | **6.297** | **3.935** | **18.584** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 9 |
