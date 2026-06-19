# Evaluation Summary

Total cases: 150

## Composite Score
- average: 70.00

## Score Breakdown
- exact_match: 70.00
- f1: 76.75

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.067 | 0.002 | 0.067 |
| summarize_hop1 | 2.295 | 2.157 | 3.428 |
| query_hop2 | 1.233 | 1.099 | 2.021 |
| retrieve_hop2 | 0.507 | 0.002 | 1.614 |
| summarize_hop2 | 1.865 | 1.623 | 3.013 |
| answer | 0.956 | 0.825 | 1.514 |
| **Total** | **6.922** | **6.402** | **10.624** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 45 |
