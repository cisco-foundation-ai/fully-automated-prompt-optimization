# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.96

## Score Breakdown
- leakage_fraction: 0.04
- privacy: 95.51
- quality: 96.40
- quality_passed: 0.96

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 7.806 | 3.006 | 34.219 |
| call_untrusted | 10.165 | 5.127 | 35.521 |
| reconstruct_response | 12.353 | 6.917 | 36.532 |
| **Total** | **30.325** | **18.446** | **91.249** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 11 |
