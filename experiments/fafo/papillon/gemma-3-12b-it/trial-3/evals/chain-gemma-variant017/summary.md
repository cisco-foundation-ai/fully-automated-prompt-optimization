# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.53

## Score Breakdown
- leakage_fraction: 0.04
- privacy: 95.57
- quality: 95.50
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.542 | 1.184 | 17.694 |
| call_untrusted | 11.957 | 11.339 | 23.037 |
| reconstruct_response | 11.548 | 11.258 | 23.081 |
| **Total** | **27.047** | **25.376** | **53.008** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 14 |
