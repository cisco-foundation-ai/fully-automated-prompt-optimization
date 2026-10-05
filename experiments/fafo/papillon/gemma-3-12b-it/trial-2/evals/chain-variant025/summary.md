# Evaluation Summary

Total cases: 111

## Composite Score
- average: 94.79

## Score Breakdown
- leakage_fraction: 0.07
- privacy: 93.19
- quality: 96.40
- quality_passed: 0.96

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 4.886 | 1.247 | 16.764 |
| call_untrusted | 11.416 | 11.063 | 20.968 |
| reconstruct_response | 12.769 | 13.090 | 22.468 |
| **Total** | **29.071** | **26.893** | **53.796** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 15 |
