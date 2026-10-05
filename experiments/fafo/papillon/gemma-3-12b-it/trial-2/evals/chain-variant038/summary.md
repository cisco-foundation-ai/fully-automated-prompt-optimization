# Evaluation Summary

Total cases: 111

## Composite Score
- average: 96.22

## Score Breakdown
- leakage_fraction: 0.05
- privacy: 95.15
- quality: 97.30
- quality_passed: 0.97

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.493 | 1.156 | 18.437 |
| call_untrusted | 11.697 | 10.871 | 23.407 |
| reconstruct_response | 12.356 | 11.387 | 24.379 |
| **Total** | **27.547** | **25.541** | **54.905** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 13 |
