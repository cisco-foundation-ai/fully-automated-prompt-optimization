# Evaluation Summary

Total cases: 111

## Composite Score
- average: 91.59

## Score Breakdown
- leakage_fraction: 0.08
- privacy: 92.19
- quality: 90.99
- quality_passed: 0.91

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 1.999 | 1.087 | 8.212 |
| call_untrusted | 3.963 | 1.902 | 16.420 |
| reconstruct_response | 2.890 | 1.454 | 9.401 |
| **Total** | **8.852** | **4.998** | **28.319** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 20 |
