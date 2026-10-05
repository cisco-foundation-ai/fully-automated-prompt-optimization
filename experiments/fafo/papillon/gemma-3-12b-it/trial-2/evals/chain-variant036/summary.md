# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.14

## Score Breakdown
- leakage_fraction: 0.04
- privacy: 95.69
- quality: 94.59
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.948 | 1.159 | 19.089 |
| call_untrusted | 11.867 | 11.777 | 22.827 |
| reconstruct_response | 12.700 | 13.304 | 24.153 |
| **Total** | **28.514** | **27.651** | **60.511** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 16 |
