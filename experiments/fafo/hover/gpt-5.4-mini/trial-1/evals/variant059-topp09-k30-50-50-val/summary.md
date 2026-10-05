# Evaluation Summary

Total cases: 300

## Composite Score
- average: 78.33

## Score Breakdown
- num_found: 2.75
- num_gold: 3.00
- partial_recall: 91.56
- recall: 78.33

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.011 | 0.002 | 0.009 |
| summarize_hop1 | 2.705 | 2.387 | 4.721 |
| query_hop2 | 0.968 | 0.782 | 1.627 |
| retrieve_hop2 | 0.990 | 1.415 | 1.565 |
| summarize_hop2 | 3.956 | 3.429 | 6.533 |
| query_hop3 | 1.106 | 0.831 | 1.926 |
| retrieve_hop3 | 0.414 | 0.002 | 1.510 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **10.149** | **9.398** | **15.926** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 65 |
