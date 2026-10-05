# Evaluation Summary

Total cases: 111

## Composite Score
- average: 97.30

## Score Breakdown
- leakage_fraction: 0.00
- privacy: 100.00
- quality: 94.59
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 2.230 | 1.167 | 8.093 |
| call_untrusted | 2.962 | 1.715 | 10.183 |
| reconstruct_response | 2.109 | 1.392 | 6.513 |
| **Total** | **7.300** | **4.666** | **21.652** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 6 |
