# Evaluation Summary

Total cases: 111

## Composite Score
- average: 94.66

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 96.53
- quality: 92.79
- quality_passed: 0.93

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 7.988 | 2.880 | 36.331 |
| call_untrusted | 10.300 | 5.672 | 28.076 |
| reconstruct_response | 10.875 | 5.945 | 33.046 |
| **Total** | **29.162** | **18.138** | **84.551** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 14 |
