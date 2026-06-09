# Evaluation Summary

Total cases: 111

## Composite Score
- average: 93.98

## Score Breakdown
- leakage_fraction: 0.07
- privacy: 93.37
- quality: 94.59
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 2.601 | 1.243 | 8.621 |
| call_untrusted | 4.050 | 2.208 | 14.114 |
| reconstruct_response | 3.341 | 1.647 | 9.535 |
| **Total** | **9.991** | **6.196** | **27.892** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 18 |
