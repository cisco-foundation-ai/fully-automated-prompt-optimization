# Evaluation Summary

Total cases: 300

## Composite Score
- average: 68.33

## Score Breakdown
- exact_match: 68.33
- f1: 76.01

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.131 | 0.002 | 0.119 |
| summarize_hop1 | 1.441 | 1.349 | 2.203 |
| query_hop2 | 1.188 | 1.075 | 1.791 |
| retrieve_hop2 | 0.359 | 0.002 | 1.586 |
| summarize_hop2 | 1.684 | 1.518 | 2.654 |
| answer | 0.939 | 0.779 | 1.768 |
| **Total** | **5.742** | **5.179** | **9.661** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 94 |
| query_hop2 | 1 |
