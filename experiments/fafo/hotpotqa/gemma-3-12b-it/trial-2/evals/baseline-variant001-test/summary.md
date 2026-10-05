# Evaluation Summary

Total cases: 300

## Composite Score
- average: 57.00

## Score Breakdown
- exact_match: 57.00
- f1: 65.91

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.003 | 0.002 | 0.007 |
| summarize_hop1 | 4.262 | 1.716 | 4.484 |
| query_hop2 | 6.551 | 1.079 | 4.597 |
| retrieve_hop2 | 1.440 | 1.387 | 1.656 |
| summarize_hop2 | 2.829 | 1.519 | 2.949 |
| answer | 1.998 | 0.940 | 2.657 |
| **Total** | **17.084** | **6.655** | **38.839** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 129 |
