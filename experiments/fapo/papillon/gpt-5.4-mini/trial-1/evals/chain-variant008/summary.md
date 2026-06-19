# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.27

## Score Breakdown
- leakage_fraction: 0.07
- privacy: 93.24
- quality: 97.30
- quality_passed: 0.97

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 1.763 | 1.002 | 6.767 |
| call_untrusted | 3.335 | 1.752 | 11.301 |
| reconstruct_response | 2.618 | 1.426 | 6.572 |
| **Total** | **7.715** | **4.484** | **20.909** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 15 |
