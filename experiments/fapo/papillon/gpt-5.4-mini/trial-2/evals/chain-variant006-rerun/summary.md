# Evaluation Summary

Total cases: 111

## Composite Score
- average: 94.14

## Score Breakdown
- leakage_fraction: 0.06
- privacy: 93.69
- quality: 94.59
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 2.353 | 1.182 | 8.153 |
| call_untrusted | 4.123 | 2.057 | 15.309 |
| reconstruct_response | 2.935 | 1.609 | 11.499 |
| **Total** | **9.411** | **5.739** | **32.136** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 15 |
