# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.86

## Score Breakdown
- leakage_fraction: 0.04
- privacy: 96.22
- quality: 95.50
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.476 | 1.262 | 16.631 |
| call_untrusted | 11.197 | 10.851 | 23.374 |
| reconstruct_response | 10.827 | 10.406 | 21.456 |
| **Total** | **25.500** | **23.811** | **50.736** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 12 |
