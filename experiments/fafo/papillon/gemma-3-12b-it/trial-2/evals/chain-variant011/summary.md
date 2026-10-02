# Evaluation Summary

Total cases: 111

## Composite Score
- average: 93.72

## Score Breakdown
- leakage_fraction: 0.05
- privacy: 94.65
- quality: 92.79
- quality_passed: 0.93

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 4.151 | 1.531 | 18.467 |
| call_untrusted | 11.969 | 11.781 | 22.622 |
| reconstruct_response | 9.225 | 7.615 | 19.911 |
| **Total** | **25.345** | **23.609** | **50.575** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 15 |
