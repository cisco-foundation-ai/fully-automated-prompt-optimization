# Evaluation Summary

Total cases: 111

## Composite Score
- average: 94.31

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 96.74
- quality: 91.89
- quality_passed: 0.92

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 6.274 | 2.235 | 29.690 |
| call_untrusted | 6.271 | 3.950 | 19.960 |
| reconstruct_response | 7.809 | 4.570 | 26.771 |
| **Total** | **20.354** | **13.355** | **65.271** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 16 |
