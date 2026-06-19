# Evaluation Summary

Total cases: 111

## Composite Score
- average: 91.46

## Score Breakdown
- leakage_fraction: 0.06
- privacy: 93.73
- quality: 89.19
- quality_passed: 0.89

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 2.504 | 1.370 | 9.304 |
| call_untrusted | 3.467 | 1.840 | 11.875 |
| reconstruct_response | 2.782 | 1.442 | 7.646 |
| **Total** | **8.753** | **4.929** | **26.866** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 23 |
