# Evaluation Summary

Total cases: 111

## Composite Score
- average: 91.86

## Score Breakdown
- leakage_fraction: 0.08
- privacy: 91.83
- quality: 91.89
- quality_passed: 0.92

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 1.913 | 1.085 | 7.052 |
| call_untrusted | 3.423 | 1.731 | 10.124 |
| reconstruct_response | 2.601 | 1.546 | 7.103 |
| **Total** | **7.936** | **5.136** | **20.796** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 22 |
