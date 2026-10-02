# Evaluation Summary

Total cases: 111

## Composite Score
- average: 91.65

## Score Breakdown
- leakage_fraction: 0.06
- privacy: 94.11
- quality: 89.19
- quality_passed: 0.89

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 4.110 | 1.627 | 19.830 |
| call_untrusted | 11.884 | 11.172 | 22.437 |
| reconstruct_response | 8.676 | 7.655 | 21.288 |
| **Total** | **24.670** | **21.174** | **47.608** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 20 |
