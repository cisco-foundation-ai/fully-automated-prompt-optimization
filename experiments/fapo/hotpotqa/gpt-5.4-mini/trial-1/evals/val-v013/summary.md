# Evaluation Summary

Total cases: 300

## Composite Score
- average: 68.67

## Score Breakdown
- exact_match: 68.67
- f1: 76.78

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.093 | 0.002 | 0.108 |
| summarize_hop1 | 1.388 | 1.310 | 2.081 |
| query_hop2 | 1.102 | 1.018 | 1.523 |
| retrieve_hop2 | 0.581 | 0.002 | 1.676 |
| summarize_hop2 | 1.535 | 1.474 | 2.147 |
| answer | 0.807 | 0.748 | 1.326 |
| **Total** | **5.505** | **4.945** | **7.958** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 93 |
| query_hop2 | 1 |
