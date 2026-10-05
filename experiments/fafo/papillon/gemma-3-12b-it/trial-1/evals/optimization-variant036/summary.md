# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.75

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 96.91
- quality: 94.59
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.474 | 1.180 | 17.981 |
| call_untrusted | 11.090 | 10.300 | 21.332 |
| reconstruct_response | 11.586 | 10.740 | 23.081 |
| **Total** | **26.150** | **22.969** | **55.431** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 12 |
