# Evaluation Summary

Total cases: 442

## Composite Score
- average: 95.60

## Score Breakdown
- leakage_fraction: 0.02
- privacy: 97.53
- quality: 93.67
- quality_passed: 0.94

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 2.092 | 1.204 | 7.534 |
| call_untrusted | 3.501 | 2.078 | 11.738 |
| reconstruct_response | 2.353 | 1.481 | 6.785 |
| **Total** | **7.947** | **5.489** | **22.669** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 45 |
