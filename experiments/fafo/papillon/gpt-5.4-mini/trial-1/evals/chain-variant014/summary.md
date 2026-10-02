# Evaluation Summary

Total cases: 111

## Composite Score
- average: 92.77

## Score Breakdown
- leakage_fraction: 0.09
- privacy: 90.94
- quality: 94.59
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 2.878 | 1.204 | 7.798 |
| call_untrusted | 4.172 | 2.236 | 15.152 |
| reconstruct_response | 3.151 | 1.773 | 10.660 |
| **Total** | **10.201** | **5.743** | **30.171** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 21 |
