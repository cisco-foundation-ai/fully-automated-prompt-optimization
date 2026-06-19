# Evaluation Summary

Total cases: 111

## Composite Score
- average: 96.09

## Score Breakdown
- leakage_fraction: 0.04
- privacy: 95.78
- quality: 96.40
- quality_passed: 0.96

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.413 | 1.166 | 17.204 |
| call_untrusted | 10.846 | 11.203 | 21.873 |
| reconstruct_response | 11.647 | 10.962 | 23.985 |
| **Total** | **25.907** | **24.536** | **54.298** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 12 |
