# Evaluation Summary

Total cases: 111

## Composite Score
- average: 97.09

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 96.89
- quality: 97.30
- quality_passed: 0.97

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.492 | 1.202 | 16.582 |
| call_untrusted | 14.449 | 14.399 | 25.381 |
| reconstruct_response | 16.179 | 15.406 | 25.150 |
| **Total** | **34.121** | **33.122** | **57.140** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 9 |
