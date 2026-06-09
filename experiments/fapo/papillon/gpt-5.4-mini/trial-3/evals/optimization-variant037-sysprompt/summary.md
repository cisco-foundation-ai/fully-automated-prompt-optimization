# Evaluation Summary

Total cases: 111

## Composite Score
- average: 96.92

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 97.45
- quality: 96.40
- quality_passed: 0.96

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 2.196 | 1.234 | 8.692 |
| call_untrusted | 4.761 | 2.420 | 17.911 |
| reconstruct_response | 3.379 | 1.887 | 11.670 |
| **Total** | **10.335** | **6.442** | **30.089** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 9 |
