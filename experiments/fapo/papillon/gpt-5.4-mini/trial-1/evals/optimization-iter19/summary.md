# Evaluation Summary

Total cases: 111

## Composite Score
- average: 96.41

## Score Breakdown
- leakage_fraction: 0.04
- privacy: 96.42
- quality: 96.40
- quality_passed: 0.96

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 2.207 | 1.160 | 8.096 |
| call_untrusted | 4.137 | 1.992 | 15.019 |
| reconstruct_response | 3.166 | 1.608 | 9.158 |
| **Total** | **9.510** | **5.350** | **28.231** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 12 |
