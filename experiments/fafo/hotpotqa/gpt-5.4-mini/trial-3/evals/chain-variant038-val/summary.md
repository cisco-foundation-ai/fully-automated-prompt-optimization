# Evaluation Summary

Total cases: 300

## Composite Score
- average: 72.33

## Score Breakdown
- exact_match: 72.33
- f1: 78.14

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.052 | 0.002 | 0.009 |
| summarize_hop1 | 1.302 | 1.257 | 1.856 |
| query_hop2 | 1.112 | 1.039 | 1.683 |
| retrieve_hop2 | 0.356 | 0.002 | 1.565 |
| summarize_hop2 | 1.392 | 1.280 | 2.008 |
| answer | 0.980 | 0.917 | 1.324 |
| **Total** | **5.195** | **4.702** | **7.708** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 83 |
