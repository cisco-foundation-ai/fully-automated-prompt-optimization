# Evaluation Summary

Total cases: 111

## Composite Score
- average: 96.47

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 97.45
- quality: 95.50
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 5.104 | 1.826 | 27.038 |
| call_untrusted | 7.222 | 3.140 | 23.503 |
| reconstruct_response | 7.137 | 3.860 | 20.513 |
| **Total** | **19.463** | **10.866** | **68.848** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 8 |
