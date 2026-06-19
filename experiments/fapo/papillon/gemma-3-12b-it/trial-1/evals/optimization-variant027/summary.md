# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.41

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 97.13
- quality: 93.69
- quality_passed: 0.94

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.481 | 1.149 | 17.797 |
| call_untrusted | 11.588 | 11.639 | 21.097 |
| reconstruct_response | 11.269 | 11.095 | 22.556 |
| **Total** | **26.338** | **24.993** | **52.642** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 13 |
