# Evaluation Summary

Total cases: 111

## Composite Score
- average: 96.47

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 96.55
- quality: 96.40
- quality_passed: 0.96

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 2.306 | 1.139 | 7.993 |
| call_untrusted | 3.944 | 1.936 | 17.183 |
| reconstruct_response | 2.724 | 1.478 | 7.151 |
| **Total** | **8.974** | **4.842** | **26.699** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 10 |
