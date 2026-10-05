# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.60

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 96.60
- quality: 94.59
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.594 | 1.225 | 18.950 |
| call_untrusted | 11.721 | 12.103 | 21.586 |
| reconstruct_response | 11.349 | 11.249 | 20.546 |
| **Total** | **26.663** | **26.249** | **54.510** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 13 |
