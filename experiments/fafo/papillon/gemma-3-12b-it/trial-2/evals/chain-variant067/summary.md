# Evaluation Summary

Total cases: 111

## Composite Score
- average: 94.54

## Score Breakdown
- leakage_fraction: 0.06
- privacy: 94.49
- quality: 94.59
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.977 | 1.261 | 20.391 |
| call_untrusted | 11.849 | 11.343 | 22.930 |
| reconstruct_response | 12.566 | 11.661 | 23.161 |
| **Total** | **28.391** | **25.568** | **62.499** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 14 |
