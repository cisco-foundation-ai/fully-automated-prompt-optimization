# Evaluation Summary

Total cases: 111

## Composite Score
- average: 94.82

## Score Breakdown
- leakage_fraction: 0.02
- privacy: 97.75
- quality: 91.89
- quality_passed: 0.92

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 2.058 | 1.175 | 6.645 |
| call_untrusted | 3.661 | 2.109 | 10.583 |
| reconstruct_response | 2.628 | 1.681 | 6.983 |
| **Total** | **8.347** | **5.758** | **23.454** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 14 |
