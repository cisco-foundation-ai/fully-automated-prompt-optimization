# Evaluation Summary

Total cases: 111

## Composite Score
- average: 97.97

## Score Breakdown
- leakage_fraction: 0.00
- privacy: 99.55
- quality: 96.40
- quality_passed: 0.96

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 2.058 | 1.118 | 6.830 |
| call_untrusted | 2.825 | 1.589 | 8.001 |
| reconstruct_response | 2.214 | 1.378 | 6.268 |
| **Total** | **7.097** | **4.621** | **20.383** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 5 |
