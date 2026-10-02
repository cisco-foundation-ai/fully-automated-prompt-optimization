# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.14

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 96.59
- quality: 93.69
- quality_passed: 0.94

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.593 | 1.202 | 18.178 |
| call_untrusted | 11.497 | 10.825 | 22.422 |
| reconstruct_response | 11.534 | 9.890 | 24.767 |
| **Total** | **26.624** | **23.819** | **57.692** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 13 |
