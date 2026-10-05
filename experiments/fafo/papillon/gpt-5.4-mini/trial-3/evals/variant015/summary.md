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
| redact_query | 1.807 | 1.069 | 6.121 |
| call_untrusted | 3.215 | 1.753 | 11.250 |
| reconstruct_response | 2.429 | 1.505 | 7.653 |
| **Total** | **7.450** | **4.489** | **23.198** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 6 |
