# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.12

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 97.45
- quality: 92.79
- quality_passed: 0.93

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 2.339 | 1.220 | 7.123 |
| call_untrusted | 4.036 | 1.968 | 13.608 |
| reconstruct_response | 2.417 | 1.693 | 7.027 |
| **Total** | **8.792** | **5.583** | **23.203** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 12 |
