# Evaluation Summary

Total cases: 111

## Composite Score
- average: 93.68

## Score Breakdown
- leakage_fraction: 0.07
- privacy: 92.77
- quality: 94.59
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 2.270 | 1.187 | 8.260 |
| call_untrusted | 3.085 | 1.821 | 11.169 |
| reconstruct_response | 2.482 | 1.466 | 7.217 |
| **Total** | **7.837** | **5.211** | **21.875** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 18 |
