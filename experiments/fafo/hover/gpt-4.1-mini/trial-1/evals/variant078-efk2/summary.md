# Evaluation Summary

Total cases: 300

## Composite Score
- average: 68.00

## Score Breakdown
- num_found: 2.60
- num_gold: 3.00
- partial_recall: 86.56
- recall: 68.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.016 | 0.010 | 0.022 |
| summarize_hop1 | 5.050 | 3.766 | 12.678 |
| query_hop2 | 0.937 | 0.764 | 1.260 |
| retrieve_hop2 | 13.587 | 12.195 | 26.035 |
| summarize_hop2 | 4.609 | 3.776 | 9.974 |
| query_hop3 | 0.961 | 0.857 | 1.503 |
| retrieve_hop3 | 15.423 | 14.738 | 23.677 |
| retrieve_mining | 0.088 | 0.023 | 0.042 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **40.671** | **38.977** | **60.200** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_mining | 96 |
