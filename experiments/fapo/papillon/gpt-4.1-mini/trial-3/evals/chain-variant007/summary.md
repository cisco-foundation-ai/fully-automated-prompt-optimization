# Evaluation Summary

Total cases: 111

## Composite Score
- average: 93.57

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 97.06
- quality: 90.09
- quality_passed: 0.90

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 4.732 | 1.757 | 19.670 |
| call_untrusted | 7.530 | 3.693 | 28.400 |
| reconstruct_response | 7.647 | 4.045 | 21.307 |
| **Total** | **19.909** | **11.238** | **65.330** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 15 |
