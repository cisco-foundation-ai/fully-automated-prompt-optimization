# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.38

## Score Breakdown
- leakage_fraction: 0.05
- privacy: 95.26
- quality: 95.50
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 2.047 | 1.124 | 7.375 |
| call_untrusted | 3.977 | 1.972 | 14.546 |
| reconstruct_response | 2.799 | 1.740 | 8.542 |
| **Total** | **8.823** | **5.037** | **25.522** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 14 |
