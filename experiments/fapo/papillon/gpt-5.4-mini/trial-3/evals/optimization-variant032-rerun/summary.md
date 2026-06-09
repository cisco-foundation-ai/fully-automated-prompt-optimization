# Evaluation Summary

Total cases: 111

## Composite Score
- average: 92.72

## Score Breakdown
- leakage_fraction: 0.04
- privacy: 96.25
- quality: 89.19
- quality_passed: 0.89

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 1.683 | 1.040 | 6.007 |
| call_untrusted | 3.752 | 2.302 | 13.422 |
| reconstruct_response | 2.671 | 1.732 | 7.221 |
| **Total** | **8.106** | **5.244** | **22.059** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 19 |
