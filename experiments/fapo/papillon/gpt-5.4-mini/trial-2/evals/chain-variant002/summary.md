# Evaluation Summary

Total cases: 111

## Composite Score
- average: 87.79

## Score Breakdown
- leakage_fraction: 0.05
- privacy: 94.50
- quality: 81.08
- quality_passed: 0.81

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 1.950 | 1.074 | 6.325 |
| call_untrusted | 3.745 | 1.931 | 13.242 |
| reconstruct_response | 0.980 | 0.935 | 1.256 |
| **Total** | **6.675** | **4.659** | **17.354** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 31 |
