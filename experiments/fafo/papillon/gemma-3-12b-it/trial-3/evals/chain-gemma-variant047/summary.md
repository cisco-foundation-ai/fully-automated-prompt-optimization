# Evaluation Summary

Total cases: 111

## Composite Score
- average: 97.05

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 96.79
- quality: 97.30
- quality_passed: 0.97

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 5.328 | 1.271 | 19.623 |
| call_untrusted | 12.240 | 11.816 | 24.756 |
| reconstruct_response | 11.758 | 10.417 | 24.357 |
| **Total** | **29.326** | **26.245** | **60.093** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 9 |
