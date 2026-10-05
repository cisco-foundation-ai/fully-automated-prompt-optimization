# Evaluation Summary

Total cases: 111

## Composite Score
- average: 97.45

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 96.69
- quality: 98.20
- quality_passed: 0.98

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.675 | 1.388 | 16.706 |
| call_untrusted | 12.319 | 12.445 | 23.608 |
| reconstruct_response | 11.800 | 11.449 | 23.237 |
| **Total** | **27.794** | **27.036** | **55.138** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 8 |
