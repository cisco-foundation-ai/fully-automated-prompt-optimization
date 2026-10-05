# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.80

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 97.00
- quality: 94.59
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 1.859 | 1.085 | 5.962 |
| call_untrusted | 3.414 | 1.898 | 13.155 |
| reconstruct_response | 2.277 | 1.261 | 8.831 |
| **Total** | **7.551** | **4.629** | **23.166** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 12 |
