# Evaluation Summary

Total cases: 300

## Composite Score
- average: 80.33

## Score Breakdown
- num_found: 2.77
- num_gold: 3.00
- num_missing: 0.23
- partial_recall: 92.33
- recall: 80.33

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.006 | 0.002 | 0.012 |
| summarize_hop1 | 3.417 | 2.902 | 6.742 |
| query_hop2 | 0.413 | 0.329 | 0.849 |
| retrieve_hop2 | 1.196 | 1.296 | 1.605 |
| summarize_hop2 | 6.808 | 5.771 | 10.359 |
| query_hop3 | 0.466 | 0.374 | 0.745 |
| retrieve_hop3 | 2.523 | 2.601 | 3.138 |
| summarize_hop3 | 9.153 | 6.928 | 13.285 |
| query_hop4 | 0.552 | 0.425 | 1.542 |
| retrieve_hop4 | 1.315 | 1.333 | 1.603 |
| query_hop5 | 0.577 | 0.474 | 0.969 |
| retrieve_hop5 | 2.279 | 2.592 | 3.146 |
| combine_retrievals | 0.000 | 0.000 | 0.001 |
| **Total** | **28.702** | **25.340** | **38.069** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop5 | 59 |
