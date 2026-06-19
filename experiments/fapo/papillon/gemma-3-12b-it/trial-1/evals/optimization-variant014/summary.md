# Evaluation Summary

Total cases: 111

## Composite Score
- average: 96.20

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 96.91
- quality: 95.50
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.694 | 1.175 | 18.160 |
| call_untrusted | 12.199 | 11.955 | 22.552 |
| reconstruct_response | 12.277 | 12.227 | 24.480 |
| **Total** | **28.169** | **26.605** | **54.673** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 11 |
