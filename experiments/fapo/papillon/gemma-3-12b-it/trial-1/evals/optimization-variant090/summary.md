# Evaluation Summary

Total cases: 111

## Composite Score
- average: 94.26

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 96.63
- quality: 91.89
- quality_passed: 0.92

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.698 | 1.242 | 19.142 |
| call_untrusted | 9.848 | 8.760 | 20.100 |
| reconstruct_response | 10.776 | 9.986 | 24.760 |
| **Total** | **24.322** | **22.620** | **50.417** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 16 |
