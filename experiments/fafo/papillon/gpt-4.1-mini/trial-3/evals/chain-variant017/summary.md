# Evaluation Summary

Total cases: 111

## Composite Score
- average: 93.84

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 96.70
- quality: 90.99
- quality_passed: 0.91

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 4.628 | 1.825 | 23.563 |
| call_untrusted | 7.124 | 3.478 | 26.646 |
| reconstruct_response | 8.183 | 4.582 | 23.944 |
| **Total** | **19.935** | **11.485** | **63.642** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 15 |
