# Evaluation Summary

Total cases: 111

## Composite Score
- average: 96.40

## Score Breakdown
- leakage_fraction: 0.04
- privacy: 96.40
- quality: 96.40
- quality_passed: 0.96

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 2.103 | 1.102 | 8.557 |
| call_untrusted | 3.606 | 2.064 | 11.890 |
| reconstruct_response | 2.390 | 1.438 | 7.923 |
| **Total** | **8.099** | **5.112** | **21.419** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 11 |
