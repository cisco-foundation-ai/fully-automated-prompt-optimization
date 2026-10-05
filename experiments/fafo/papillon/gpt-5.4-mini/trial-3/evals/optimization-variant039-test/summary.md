# Evaluation Summary

Total cases: 442

## Composite Score
- average: 95.25

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 97.29
- quality: 93.21
- quality_passed: 0.93

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 2.131 | 1.220 | 7.124 |
| call_untrusted | 3.588 | 2.062 | 12.145 |
| reconstruct_response | 2.572 | 1.540 | 8.409 |
| **Total** | **8.291** | **5.511** | **25.984** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 46 |
