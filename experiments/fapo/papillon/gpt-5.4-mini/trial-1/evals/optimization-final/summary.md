# Evaluation Summary

Total cases: 111

## Composite Score
- average: 93.63

## Score Breakdown
- leakage_fraction: 0.06
- privacy: 94.46
- quality: 92.79
- quality_passed: 0.93

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 2.352 | 1.157 | 7.707 |
| call_untrusted | 4.492 | 2.299 | 15.954 |
| reconstruct_response | 3.222 | 1.796 | 11.181 |
| **Total** | **10.066** | **6.103** | **27.825** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 17 |
