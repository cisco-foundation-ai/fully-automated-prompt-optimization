# Evaluation Summary

Total cases: 111

## Composite Score
- average: 93.29

## Score Breakdown
- leakage_fraction: 0.06
- privacy: 93.79
- quality: 92.79
- quality_passed: 0.93

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 2.196 | 1.262 | 7.036 |
| call_untrusted | 4.153 | 2.095 | 15.260 |
| reconstruct_response | 3.051 | 1.656 | 10.901 |
| **Total** | **9.399** | **5.703** | **26.857** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 19 |
