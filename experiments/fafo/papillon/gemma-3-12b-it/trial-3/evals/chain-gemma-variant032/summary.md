# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.22

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 96.75
- quality: 93.69
- quality_passed: 0.94

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.373 | 1.227 | 17.763 |
| call_untrusted | 10.801 | 11.330 | 20.822 |
| reconstruct_response | 10.905 | 11.165 | 21.239 |
| **Total** | **25.079** | **25.403** | **54.007** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 14 |
