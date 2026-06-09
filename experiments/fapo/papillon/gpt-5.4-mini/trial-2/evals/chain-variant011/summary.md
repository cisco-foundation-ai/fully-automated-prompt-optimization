# Evaluation Summary

Total cases: 111

## Composite Score
- average: 94.14

## Score Breakdown
- leakage_fraction: 0.05
- privacy: 94.59
- quality: 93.69
- quality_passed: 0.94

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 2.184 | 1.227 | 7.538 |
| call_untrusted | 3.817 | 2.097 | 15.163 |
| reconstruct_response | 2.834 | 1.731 | 8.755 |
| **Total** | **8.835** | **5.553** | **27.592** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 14 |
