# Evaluation Summary

Total cases: 111

## Composite Score
- average: 93.23

## Score Breakdown
- leakage_fraction: 0.08
- privacy: 91.87
- quality: 94.59
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 5.042 | 1.825 | 18.683 |
| call_untrusted | 6.964 | 2.937 | 28.473 |
| reconstruct_response | 7.023 | 3.887 | 23.116 |
| **Total** | **19.028** | **10.693** | **62.404** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 17 |
