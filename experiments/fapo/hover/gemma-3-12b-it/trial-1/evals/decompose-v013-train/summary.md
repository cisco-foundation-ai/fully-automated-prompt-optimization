# Evaluation Summary

Total cases: 150

## Composite Score
- average: 70.67

## Score Breakdown
- num_found: 2.69
- num_gold: 3.00
- num_missing: 0.31
- partial_recall: 89.78
- recall: 70.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.125 | 0.027 | 1.325 |
| summarize_hop1 | 10.327 | 9.848 | 15.695 |
| query_hop2 | 0.359 | 0.317 | 0.738 |
| retrieve_hop2 | 1.732 | 1.329 | 1.663 |
| summarize_hop2 | 15.963 | 13.841 | 23.222 |
| query_hop3 | 0.364 | 0.330 | 0.549 |
| retrieve_hop3 | 1.399 | 1.377 | 1.648 |
| combine_retrievals | 0.010 | 0.010 | 0.019 |
| **Total** | **30.279** | **28.138** | **47.708** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3_trunc | 44 |
