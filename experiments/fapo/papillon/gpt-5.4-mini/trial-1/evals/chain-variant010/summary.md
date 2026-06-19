# Evaluation Summary

Total cases: 111

## Composite Score
- average: 91.73

## Score Breakdown
- leakage_fraction: 0.07
- privacy: 93.37
- quality: 90.09
- quality_passed: 0.90

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 2.292 | 1.310 | 8.374 |
| call_untrusted | 3.410 | 1.890 | 13.681 |
| reconstruct_response | 2.467 | 1.550 | 6.282 |
| **Total** | **8.169** | **5.048** | **21.324** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 23 |
