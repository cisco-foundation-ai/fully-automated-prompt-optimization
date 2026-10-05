# Evaluation Summary

Total cases: 111

## Composite Score
- average: 97.21

## Score Breakdown
- leakage_fraction: 0.04
- privacy: 96.23
- quality: 98.20
- quality_passed: 0.98

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 2.587 | 1.420 | 9.083 |
| call_untrusted | 4.272 | 2.312 | 15.001 |
| reconstruct_response | 3.595 | 1.902 | 14.547 |
| **Total** | **10.454** | **6.102** | **31.331** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 9 |
