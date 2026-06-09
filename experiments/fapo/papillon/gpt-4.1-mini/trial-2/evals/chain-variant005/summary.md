# Evaluation Summary

Total cases: 111

## Composite Score
- average: 93.27

## Score Breakdown
- leakage_fraction: 0.05
- privacy: 94.65
- quality: 91.89
- quality_passed: 0.92

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 6.352 | 2.171 | 31.247 |
| call_untrusted | 6.666 | 3.786 | 18.194 |
| reconstruct_response | 7.549 | 4.267 | 26.780 |
| **Total** | **20.567** | **12.669** | **66.604** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 19 |
