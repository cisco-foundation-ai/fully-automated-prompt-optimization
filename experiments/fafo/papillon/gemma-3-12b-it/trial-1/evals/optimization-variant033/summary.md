# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.08

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 97.36
- quality: 92.79
- quality_passed: 0.93

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.456 | 1.170 | 17.610 |
| call_untrusted | 11.138 | 10.706 | 21.638 |
| reconstruct_response | 11.212 | 10.147 | 25.187 |
| **Total** | **25.807** | **22.334** | **56.676** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 12 |
