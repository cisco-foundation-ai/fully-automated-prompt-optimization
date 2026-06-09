# Evaluation Summary

Total cases: 111

## Composite Score
- average: 96.23

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 96.97
- quality: 95.50
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.959 | 1.352 | 20.700 |
| call_untrusted | 12.446 | 11.582 | 25.362 |
| reconstruct_response | 12.648 | 11.246 | 31.847 |
| **Total** | **29.053** | **25.950** | **61.679** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 11 |
