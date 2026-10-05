# Evaluation Summary

Total cases: 300

## Composite Score
- average: 21.00

## Score Breakdown
- num_found: 1.81
- num_gold: 3.00
- partial_recall: 60.44
- recall: 21.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.003 | 0.002 | 0.005 |
| summarize_hop1 | 2.664 | 2.112 | 4.026 |
| query_hop2 | 0.688 | 0.522 | 1.044 |
| retrieve_hop2 | 0.173 | 0.002 | 1.327 |
| summarize_hop2 | 2.802 | 2.346 | 4.821 |
| query_hop3 | 0.611 | 0.544 | 1.115 |
| retrieve_hop3 | 0.580 | 0.002 | 1.642 |
| retrieve_hop3b | 0.248 | 0.002 | 1.557 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **7.770** | **6.779** | **13.815** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3b | 237 |
