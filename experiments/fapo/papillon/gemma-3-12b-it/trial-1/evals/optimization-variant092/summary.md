# Evaluation Summary

Total cases: 111

## Composite Score
- average: 96.31

## Score Breakdown
- leakage_fraction: 0.04
- privacy: 96.23
- quality: 96.40
- quality_passed: 0.96

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.536 | 1.231 | 18.452 |
| call_untrusted | 15.141 | 15.165 | 24.739 |
| reconstruct_response | 16.076 | 16.205 | 26.484 |
| **Total** | **34.753** | **34.535** | **57.287** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 12 |
