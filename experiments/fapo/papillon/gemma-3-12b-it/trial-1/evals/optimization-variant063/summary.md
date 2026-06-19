# Evaluation Summary

Total cases: 111

## Composite Score
- average: 92.83

## Score Breakdown
- leakage_fraction: 0.04
- privacy: 96.47
- quality: 89.19
- quality_passed: 0.89

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.493 | 1.153 | 14.699 |
| call_untrusted | 10.690 | 10.970 | 22.719 |
| reconstruct_response | 10.782 | 10.848 | 22.133 |
| **Total** | **24.965** | **24.392** | **55.133** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 20 |
