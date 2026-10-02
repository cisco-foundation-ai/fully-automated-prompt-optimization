# Evaluation Summary

Total cases: 111

## Composite Score
- average: 96.68

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 96.97
- quality: 96.40
- quality_passed: 0.96

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.786 | 1.311 | 19.348 |
| call_untrusted | 13.193 | 11.575 | 28.954 |
| reconstruct_response | 12.331 | 11.935 | 25.634 |
| **Total** | **29.310** | **27.058** | **60.060** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 10 |
