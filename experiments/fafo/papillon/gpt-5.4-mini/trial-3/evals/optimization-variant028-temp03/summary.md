# Evaluation Summary

Total cases: 111

## Composite Score
- average: 96.02

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 97.45
- quality: 94.59
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 2.321 | 1.124 | 8.484 |
| call_untrusted | 3.407 | 1.860 | 10.808 |
| reconstruct_response | 2.372 | 1.397 | 7.114 |
| **Total** | **8.100** | **4.956** | **21.860** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 10 |
