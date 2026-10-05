# Evaluation Summary

Total cases: 111

## Composite Score
- average: 92.18

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 96.97
- quality: 87.39
- quality_passed: 0.87

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 6.173 | 1.411 | 22.255 |
| call_untrusted | 12.862 | 11.952 | 27.718 |
| reconstruct_response | 13.806 | 11.744 | 32.240 |
| **Total** | **32.841** | **27.926** | **72.620** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 20 |
