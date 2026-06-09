# Evaluation Summary

Total cases: 111

## Composite Score
- average: 96.42

## Score Breakdown
- leakage_fraction: 0.06
- privacy: 93.74
- quality: 99.10
- quality_passed: 0.99

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.653 | 1.211 | 17.001 |
| call_untrusted | 11.765 | 11.758 | 20.793 |
| reconstruct_response | 12.475 | 11.826 | 22.689 |
| **Total** | **27.892** | **25.864** | **53.187** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 12 |
