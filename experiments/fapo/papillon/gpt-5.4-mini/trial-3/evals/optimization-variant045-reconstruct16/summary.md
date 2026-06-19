# Evaluation Summary

Total cases: 111

## Composite Score
- average: 98.05

## Score Breakdown
- leakage_fraction: 0.01
- privacy: 98.80
- quality: 97.30
- quality_passed: 0.97

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 1.934 | 1.085 | 6.627 |
| call_untrusted | 3.448 | 1.757 | 12.322 |
| reconstruct_response | 2.533 | 1.367 | 8.502 |
| **Total** | **7.914** | **4.823** | **23.416** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 5 |
