# Evaluation Summary

Total cases: 111

## Composite Score
- average: 94.85

## Score Breakdown
- leakage_fraction: 0.04
- privacy: 96.01
- quality: 93.69
- quality_passed: 0.94

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.841 | 1.321 | 16.586 |
| call_untrusted | 11.418 | 11.570 | 19.323 |
| reconstruct_response | 11.308 | 10.563 | 20.405 |
| **Total** | **26.567** | **24.851** | **50.978** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 13 |
