# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.50

## Score Breakdown
- leakage_fraction: 0.00
- privacy: 100.00
- quality: 90.99
- quality_passed: 0.91

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 1.800 | 1.193 | 5.108 |
| call_untrusted | 3.353 | 1.812 | 10.477 |
| reconstruct_response | 2.427 | 1.547 | 6.686 |
| **Total** | **7.580** | **4.705** | **21.649** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 10 |
