# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.90

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 97.21
- quality: 94.59
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 1.838 | 1.206 | 6.362 |
| call_untrusted | 3.248 | 1.805 | 12.121 |
| reconstruct_response | 2.493 | 1.457 | 7.753 |
| **Total** | **7.580** | **4.594** | **22.791** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 13 |
