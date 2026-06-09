# Evaluation Summary

Total cases: 111

## Composite Score
- average: 94.32

## Score Breakdown
- leakage_fraction: 0.05
- privacy: 94.95
- quality: 93.69
- quality_passed: 0.94

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 2.532 | 1.209 | 8.753 |
| call_untrusted | 4.031 | 2.117 | 12.785 |
| reconstruct_response | 2.960 | 1.768 | 8.395 |
| **Total** | **9.523** | **6.100** | **26.633** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 16 |
