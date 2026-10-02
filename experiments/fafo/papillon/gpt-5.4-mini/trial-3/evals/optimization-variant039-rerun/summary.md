# Evaluation Summary

Total cases: 111

## Composite Score
- average: 98.57

## Score Breakdown
- leakage_fraction: 0.01
- privacy: 98.95
- quality: 98.20
- quality_passed: 0.98

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 2.414 | 1.139 | 8.575 |
| call_untrusted | 3.782 | 1.926 | 15.517 |
| reconstruct_response | 2.828 | 1.538 | 10.405 |
| **Total** | **9.024** | **5.224** | **30.683** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 5 |
