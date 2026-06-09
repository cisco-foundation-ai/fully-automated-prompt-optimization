# Evaluation Summary

Total cases: 300

## Composite Score
- average: 20.00

## Score Breakdown
- num_found: 1.79
- num_gold: 3.00
- partial_recall: 59.78
- recall: 20.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.009 | 0.002 | 0.005 |
| summarize_hop1 | 3.528 | 3.151 | 6.364 |
| query_hop2 | 0.813 | 0.518 | 1.390 |
| retrieve_hop2 | 0.795 | 0.002 | 1.626 |
| summarize_hop2 | 5.039 | 4.218 | 9.738 |
| query_hop3 | 0.692 | 0.518 | 1.018 |
| retrieve_hop3 | 0.823 | 1.109 | 1.626 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **11.700** | **10.674** | **20.235** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 240 |
