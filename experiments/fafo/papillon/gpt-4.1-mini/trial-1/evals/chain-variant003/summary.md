# Evaluation Summary

Total cases: 111

## Composite Score
- average: 94.44

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 96.98
- quality: 91.89
- quality_passed: 0.92

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 5.197 | 1.924 | 29.828 |
| call_untrusted | 6.811 | 3.653 | 22.513 |
| reconstruct_response | 9.168 | 4.417 | 27.502 |
| **Total** | **21.176** | **11.780** | **66.385** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 14 |
