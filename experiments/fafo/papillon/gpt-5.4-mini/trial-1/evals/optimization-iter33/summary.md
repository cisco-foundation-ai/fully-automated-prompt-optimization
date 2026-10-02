# Evaluation Summary

Total cases: 111

## Composite Score
- average: 93.19

## Score Breakdown
- leakage_fraction: 0.06
- privacy: 93.58
- quality: 92.79
- quality_passed: 0.93

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 2.239 | 1.190 | 7.546 |
| call_untrusted | 4.278 | 2.152 | 16.324 |
| reconstruct_response | 2.952 | 1.635 | 10.064 |
| **Total** | **9.468** | **5.764** | **27.425** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 20 |
