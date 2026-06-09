# Evaluation Summary

Total cases: 111

## Composite Score
- average: 96.46

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 96.52
- quality: 96.40
- quality_passed: 0.96

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.584 | 1.322 | 18.050 |
| call_untrusted | 11.985 | 11.063 | 22.463 |
| reconstruct_response | 12.006 | 11.143 | 23.860 |
| **Total** | **27.575** | **24.809** | **53.385** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 10 |
