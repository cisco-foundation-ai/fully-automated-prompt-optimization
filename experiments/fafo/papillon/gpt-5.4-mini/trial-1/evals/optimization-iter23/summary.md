# Evaluation Summary

Total cases: 111

## Composite Score
- average: 94.29

## Score Breakdown
- leakage_fraction: 0.07
- privacy: 93.09
- quality: 95.50
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 2.202 | 1.213 | 7.134 |
| call_untrusted | 3.962 | 1.898 | 15.121 |
| reconstruct_response | 2.985 | 1.648 | 12.455 |
| **Total** | **9.149** | **5.661** | **32.749** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 16 |
