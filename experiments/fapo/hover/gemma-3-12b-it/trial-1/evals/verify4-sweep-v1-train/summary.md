# Evaluation Summary

Total cases: 150

## Composite Score
- average: 92.67

## Score Breakdown
- num_found: 2.93
- num_gold: 3.00
- num_missing: 0.07
- partial_recall: 97.56
- recall: 92.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 5.673 | 5.230 | 9.676 |
| summarize_hop1 | 1.640 | 1.394 | 3.425 |
| retrieve_hop2 | 8.202 | 8.076 | 14.378 |
| summarize_hop2 | 1.503 | 1.293 | 3.124 |
| retrieve_hop3 | 4.514 | 3.574 | 12.459 |
| summarize_hop3 | 1.436 | 1.300 | 2.960 |
| retrieve_hop4 | 2.152 | 1.622 | 6.083 |
| entity_sweep | 39.856 | 40.852 | 47.695 |
| combine_retrievals | 0.089 | 0.085 | 0.159 |
| **Total** | **65.064** | **64.709** | **82.412** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_sweep | 11 |
