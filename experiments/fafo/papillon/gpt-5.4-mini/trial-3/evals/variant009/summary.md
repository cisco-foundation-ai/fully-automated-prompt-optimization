# Evaluation Summary

Total cases: 111

## Composite Score
- average: 96.25

## Score Breakdown
- leakage_fraction: 0.02
- privacy: 97.90
- quality: 94.59
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 1.880 | 1.157 | 6.927 |
| call_untrusted | 3.467 | 1.804 | 13.197 |
| reconstruct_response | 2.544 | 1.482 | 8.035 |
| **Total** | **7.891** | **4.921** | **23.526** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 9 |
