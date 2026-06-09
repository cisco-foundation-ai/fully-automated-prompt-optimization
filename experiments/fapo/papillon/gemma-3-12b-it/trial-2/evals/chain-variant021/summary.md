# Evaluation Summary

Total cases: 111

## Composite Score
- average: 94.99

## Score Breakdown
- leakage_fraction: 0.04
- privacy: 96.29
- quality: 93.69
- quality_passed: 0.94

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.672 | 1.399 | 16.025 |
| call_untrusted | 11.679 | 11.201 | 21.894 |
| reconstruct_response | 11.432 | 9.835 | 23.944 |
| **Total** | **26.783** | **22.646** | **56.899** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 14 |
