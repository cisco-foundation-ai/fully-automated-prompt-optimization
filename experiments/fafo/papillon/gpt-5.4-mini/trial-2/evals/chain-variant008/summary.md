# Evaluation Summary

Total cases: 111

## Composite Score
- average: 94.82

## Score Breakdown
- leakage_fraction: 0.04
- privacy: 95.95
- quality: 93.69
- quality_passed: 0.94

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 1.957 | 1.045 | 6.479 |
| call_untrusted | 3.444 | 1.798 | 12.253 |
| reconstruct_response | 2.394 | 1.302 | 7.573 |
| **Total** | **7.794** | **4.461** | **23.111** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 13 |
