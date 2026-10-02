# Evaluation Summary

Total cases: 111

## Composite Score
- average: 94.89

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 97.00
- quality: 92.79
- quality_passed: 0.93

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 2.291 | 1.136 | 8.812 |
| call_untrusted | 3.443 | 1.683 | 13.852 |
| reconstruct_response | 2.081 | 1.381 | 5.715 |
| **Total** | **7.815** | **4.758** | **22.754** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 12 |
