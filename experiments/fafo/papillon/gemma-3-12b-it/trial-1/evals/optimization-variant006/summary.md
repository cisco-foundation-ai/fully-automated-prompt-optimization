# Evaluation Summary

Total cases: 111

## Composite Score
- average: 92.15

## Score Breakdown
- leakage_fraction: 0.05
- privacy: 95.11
- quality: 89.19
- quality_passed: 0.89

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.882 | 1.258 | 20.786 |
| call_untrusted | 11.653 | 10.597 | 21.763 |
| reconstruct_response | 10.046 | 9.142 | 24.383 |
| **Total** | **25.581** | **21.412** | **57.703** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 20 |
