# Evaluation Summary

Total cases: 300

## Composite Score
- average: 50.67

## Score Breakdown
- num_found: 2.40
- num_gold: 3.00
- partial_recall: 80.00
- recall: 50.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.908 | 0.483 | 1.533 |
| summarize_hop1 | 6.327 | 5.268 | 13.763 |
| query_hop2 | 0.892 | 0.777 | 1.462 |
| retrieve_hop2 | 1.040 | 1.114 | 1.574 |
| summarize_hop2 | 9.209 | 7.354 | 21.021 |
| query_hop3 | 1.289 | 1.000 | 2.344 |
| retrieve_hop3 | 0.954 | 1.115 | 1.592 |
| combine_retrievals | 0.000 | 0.000 | 0.001 |
| **Total** | **20.620** | **18.209** | **35.053** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 148 |
