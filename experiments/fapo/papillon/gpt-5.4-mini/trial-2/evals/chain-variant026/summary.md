# Evaluation Summary

Total cases: 111

## Composite Score
- average: 93.99

## Score Breakdown
- leakage_fraction: 0.07
- privacy: 93.39
- quality: 94.59
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 2.276 | 1.194 | 7.353 |
| call_untrusted | 3.587 | 2.001 | 11.948 |
| reconstruct_response | 2.621 | 1.579 | 7.510 |
| **Total** | **8.484** | **5.550** | **22.709** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 16 |
