# Evaluation Summary

Total cases: 111

## Composite Score
- average: 94.97

## Score Breakdown
- leakage_fraction: 0.05
- privacy: 95.35
- quality: 94.59
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 1.875 | 1.093 | 6.148 |
| call_untrusted | 3.102 | 1.691 | 10.249 |
| reconstruct_response | 2.300 | 1.266 | 7.096 |
| **Total** | **7.278** | **4.203** | **20.959** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 13 |
