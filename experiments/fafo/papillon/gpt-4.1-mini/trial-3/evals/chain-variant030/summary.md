# Evaluation Summary

Total cases: 111

## Composite Score
- average: 92.87

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 96.55
- quality: 89.19
- quality_passed: 0.89

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 6.409 | 2.025 | 31.429 |
| call_untrusted | 10.008 | 4.987 | 31.294 |
| reconstruct_response | 7.983 | 4.452 | 23.105 |
| **Total** | **24.399** | **13.345** | **77.090** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 16 |
