# Evaluation Summary

Total cases: 442

## Composite Score
- average: 93.80

## Score Breakdown
- leakage_fraction: 0.06
- privacy: 94.17
- quality: 93.44
- quality_passed: 0.93

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 4.806 | 2.072 | 19.308 |
| call_untrusted | 5.694 | 3.557 | 17.560 |
| reconstruct_response | 6.675 | 4.059 | 20.772 |
| **Total** | **17.175** | **11.296** | **53.838** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 66 |
