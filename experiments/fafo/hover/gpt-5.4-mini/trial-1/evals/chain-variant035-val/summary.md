# Evaluation Summary

Total cases: 300

## Composite Score
- average: 73.67

## Score Breakdown
- num_found: 2.69
- num_gold: 3.00
- partial_recall: 89.78
- recall: 73.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.004 | 0.002 | 0.006 |
| summarize_hop1 | 2.409 | 2.281 | 3.825 |
| query_hop2 | 0.811 | 0.682 | 1.038 |
| retrieve_hop2 | 1.172 | 1.289 | 1.673 |
| summarize_hop2 | 3.374 | 3.096 | 5.112 |
| query_hop3 | 0.869 | 0.732 | 1.298 |
| retrieve_hop3 | 0.634 | 0.003 | 1.620 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **9.272** | **8.796** | **14.004** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 79 |
