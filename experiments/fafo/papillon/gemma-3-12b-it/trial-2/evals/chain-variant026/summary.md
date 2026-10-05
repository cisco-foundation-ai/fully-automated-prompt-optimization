# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.98

## Score Breakdown
- leakage_fraction: 0.04
- privacy: 95.56
- quality: 96.40
- quality_passed: 0.96

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.684 | 1.268 | 17.225 |
| call_untrusted | 11.966 | 10.615 | 28.292 |
| reconstruct_response | 13.327 | 13.361 | 29.505 |
| **Total** | **28.976** | **25.696** | **64.655** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 10 |
