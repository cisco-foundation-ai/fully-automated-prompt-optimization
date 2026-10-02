# Evaluation Summary

Total cases: 300

## Composite Score
- average: 81.00

## Score Breakdown
- num_found: 2.79
- num_gold: 3.00
- num_missing: 0.21
- partial_recall: 93.00
- recall: 81.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.003 | 0.002 | 0.011 |
| summarize_hop1 | 3.110 | 2.736 | 5.608 |
| query_hop2 | 0.399 | 0.319 | 0.781 |
| retrieve_hop2 | 0.873 | 1.216 | 1.604 |
| summarize_hop2 | 6.248 | 5.977 | 9.808 |
| query_hop3 | 0.433 | 0.371 | 0.673 |
| retrieve_hop3 | 1.426 | 1.478 | 3.119 |
| summarize_hop3 | 6.404 | 5.957 | 11.596 |
| query_hop4 | 0.471 | 0.414 | 0.773 |
| retrieve_hop4 | 1.387 | 1.500 | 1.659 |
| query_hop5 | 0.519 | 0.456 | 0.820 |
| retrieve_hop5 | 2.129 | 1.963 | 3.196 |
| combine_retrievals | 0.000 | 0.000 | 0.001 |
| **Total** | **23.401** | **22.913** | **32.244** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop5 | 57 |
