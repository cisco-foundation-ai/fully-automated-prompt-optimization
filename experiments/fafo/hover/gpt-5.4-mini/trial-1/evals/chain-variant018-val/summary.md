# Evaluation Summary

Total cases: 300

## Composite Score
- average: 67.33

## Score Breakdown
- num_found: 2.63
- num_gold: 3.00
- partial_recall: 87.67
- recall: 67.33

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.003 | 0.002 | 0.004 |
| summarize_hop1 | 2.252 | 2.109 | 3.616 |
| query_hop2 | 0.914 | 0.688 | 1.171 |
| retrieve_hop2 | 1.216 | 1.472 | 1.655 |
| summarize_hop2 | 1.978 | 1.769 | 2.920 |
| query_hop3 | 0.591 | 0.577 | 0.817 |
| retrieve_hop3 | 0.133 | 0.002 | 1.496 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **7.089** | **6.621** | **10.861** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 98 |
