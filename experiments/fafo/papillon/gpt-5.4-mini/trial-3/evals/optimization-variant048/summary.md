# Evaluation Summary

Total cases: 111

## Composite Score
- average: 97.75

## Score Breakdown
- leakage_fraction: 0.01
- privacy: 99.10
- quality: 96.40
- quality_passed: 0.96

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 1.984 | 1.151 | 7.306 |
| call_untrusted | 2.888 | 1.692 | 8.349 |
| reconstruct_response | 1.962 | 1.291 | 4.870 |
| **Total** | **6.834** | **4.772** | **18.961** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 5 |
