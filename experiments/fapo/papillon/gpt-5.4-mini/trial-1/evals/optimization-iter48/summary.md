# Evaluation Summary

Total cases: 111

## Composite Score
- average: 94.82

## Score Breakdown
- leakage_fraction: 0.06
- privacy: 94.14
- quality: 95.50
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 2.225 | 1.208 | 8.071 |
| call_untrusted | 4.083 | 2.032 | 13.558 |
| reconstruct_response | 3.084 | 1.744 | 8.377 |
| **Total** | **9.392** | **5.714** | **23.988** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 16 |
