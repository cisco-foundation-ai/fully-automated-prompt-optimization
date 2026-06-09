# Evaluation Summary

Total cases: 300

## Composite Score
- average: 69.67

## Score Breakdown
- exact_match: 69.67
- f1: 77.27

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.097 | 0.002 | 0.102 |
| summarize_hop1 | 1.383 | 1.328 | 2.075 |
| query_hop2 | 1.154 | 1.054 | 2.021 |
| retrieve_hop2 | 0.777 | 0.003 | 1.652 |
| summarize_hop2 | 1.673 | 1.550 | 2.280 |
| answer | 0.823 | 0.727 | 1.178 |
| **Total** | **5.907** | **5.361** | **8.583** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 90 |
| query_hop2 | 1 |
