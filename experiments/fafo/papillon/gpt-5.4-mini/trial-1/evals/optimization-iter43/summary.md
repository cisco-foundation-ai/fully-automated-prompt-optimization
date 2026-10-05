# Evaluation Summary

Total cases: 111

## Composite Score
- average: 93.92

## Score Breakdown
- leakage_fraction: 0.07
- privacy: 93.24
- quality: 94.59
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 2.287 | 1.146 | 7.417 |
| call_untrusted | 4.084 | 1.874 | 15.726 |
| reconstruct_response | 3.112 | 1.680 | 10.870 |
| **Total** | **9.484** | **5.554** | **28.711** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 18 |
