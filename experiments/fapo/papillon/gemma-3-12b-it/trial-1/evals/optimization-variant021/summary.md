# Evaluation Summary

Total cases: 111

## Composite Score
- average: 96.19

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 96.89
- quality: 95.50
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.814 | 1.271 | 19.534 |
| call_untrusted | 12.890 | 12.512 | 26.552 |
| reconstruct_response | 13.188 | 12.989 | 27.478 |
| **Total** | **29.892** | **27.519** | **59.973** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 11 |
