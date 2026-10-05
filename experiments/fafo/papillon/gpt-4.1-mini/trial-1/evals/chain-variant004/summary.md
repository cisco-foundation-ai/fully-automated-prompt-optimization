# Evaluation Summary

Total cases: 111

## Composite Score
- average: 96.18

## Score Breakdown
- leakage_fraction: 0.04
- privacy: 95.96
- quality: 96.40
- quality_passed: 0.96

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 7.390 | 2.569 | 27.467 |
| call_untrusted | 6.471 | 3.724 | 20.928 |
| reconstruct_response | 7.966 | 4.654 | 24.103 |
| **Total** | **21.827** | **13.184** | **70.963** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 11 |
