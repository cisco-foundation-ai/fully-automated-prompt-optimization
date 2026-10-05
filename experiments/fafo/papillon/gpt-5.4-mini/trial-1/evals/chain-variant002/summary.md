# Evaluation Summary

Total cases: 111

## Composite Score
- average: 92.56

## Score Breakdown
- leakage_fraction: 0.07
- privacy: 93.22
- quality: 91.89
- quality_passed: 0.92

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 2.119 | 1.187 | 7.056 |
| call_untrusted | 3.053 | 1.709 | 10.555 |
| reconstruct_response | 1.128 | 0.994 | 1.421 |
| **Total** | **6.300** | **4.456** | **14.988** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 18 |
