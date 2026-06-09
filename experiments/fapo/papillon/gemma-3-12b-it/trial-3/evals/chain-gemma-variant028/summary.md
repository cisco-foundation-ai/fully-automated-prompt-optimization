# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.19

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 96.69
- quality: 93.69
- quality_passed: 0.94

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.520 | 1.179 | 16.820 |
| call_untrusted | 11.366 | 10.956 | 22.882 |
| reconstruct_response | 11.437 | 10.898 | 23.319 |
| **Total** | **26.323** | **25.058** | **55.890** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 14 |
