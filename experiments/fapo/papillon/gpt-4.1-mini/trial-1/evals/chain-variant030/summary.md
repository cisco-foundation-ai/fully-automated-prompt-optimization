# Evaluation Summary

Total cases: 111

## Composite Score
- average: 94.79

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 96.79
- quality: 92.79
- quality_passed: 0.93

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 7.191 | 2.657 | 36.806 |
| call_untrusted | 8.255 | 3.879 | 24.126 |
| reconstruct_response | 8.040 | 4.693 | 28.934 |
| **Total** | **23.485** | **14.806** | **79.141** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 14 |
