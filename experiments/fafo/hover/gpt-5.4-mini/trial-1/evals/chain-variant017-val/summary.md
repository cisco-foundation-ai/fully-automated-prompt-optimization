# Evaluation Summary

Total cases: 300

## Composite Score
- average: 70.00

## Score Breakdown
- num_found: 2.65
- num_gold: 3.00
- partial_recall: 88.33
- recall: 70.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.008 | 0.002 | 0.004 |
| summarize_hop1 | 2.426 | 2.151 | 3.717 |
| query_hop2 | 0.795 | 0.723 | 1.120 |
| retrieve_hop2 | 1.416 | 1.480 | 1.685 |
| summarize_hop2 | 1.881 | 1.796 | 2.793 |
| query_hop3 | 0.756 | 0.572 | 1.049 |
| retrieve_hop3 | 0.109 | 0.002 | 1.490 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **7.391** | **6.905** | **10.588** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 90 |
