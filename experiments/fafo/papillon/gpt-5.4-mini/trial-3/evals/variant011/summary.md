# Evaluation Summary

Total cases: 111

## Composite Score
- average: 98.15

## Score Breakdown
- leakage_fraction: 0.00
- privacy: 99.91
- quality: 96.40
- quality_passed: 0.96

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 1.986 | 0.989 | 8.245 |
| call_untrusted | 2.998 | 1.724 | 8.366 |
| reconstruct_response | 2.201 | 1.397 | 6.704 |
| **Total** | **7.185** | **4.411** | **19.441** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 5 |
