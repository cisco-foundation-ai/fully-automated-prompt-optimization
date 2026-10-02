# Evaluation Summary

Total cases: 300

## Composite Score
- average: 67.33

## Score Breakdown
- exact_match: 67.33
- f1: 74.32

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.034 | 0.002 | 0.012 |
| summarize_hop1 | 3.551 | 3.053 | 6.753 |
| query_hop2 | 1.941 | 1.723 | 3.170 |
| retrieve_hop2 | 0.273 | 0.002 | 1.515 |
| summarize_hop2 | 3.269 | 3.029 | 5.372 |
| answer | 2.163 | 1.659 | 4.340 |
| **Total** | **11.232** | **10.309** | **17.062** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 98 |
