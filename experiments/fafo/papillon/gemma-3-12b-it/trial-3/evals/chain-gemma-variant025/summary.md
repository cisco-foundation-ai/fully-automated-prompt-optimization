# Evaluation Summary

Total cases: 111

## Composite Score
- average: 97.44

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 96.69
- quality: 98.20
- quality_passed: 0.98

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.799 | 1.342 | 19.914 |
| call_untrusted | 11.882 | 12.176 | 21.876 |
| reconstruct_response | 11.840 | 11.841 | 23.820 |
| **Total** | **27.521** | **27.088** | **56.829** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 9 |
