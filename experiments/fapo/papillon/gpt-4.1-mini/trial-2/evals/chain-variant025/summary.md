# Evaluation Summary

Total cases: 111

## Composite Score
- average: 93.78

## Score Breakdown
- leakage_fraction: 0.09
- privacy: 91.16
- quality: 96.40
- quality_passed: 0.96

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 7.247 | 2.236 | 31.674 |
| call_untrusted | 7.138 | 4.570 | 21.952 |
| reconstruct_response | 7.056 | 4.114 | 20.805 |
| **Total** | **21.441** | **12.475** | **72.303** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 17 |
