# Evaluation Summary

Total cases: 300

## Composite Score
- average: 75.33

## Score Breakdown
- num_found: 2.72
- num_gold: 3.00
- partial_recall: 90.67
- recall: 75.33

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.008 | 0.002 | 0.007 |
| summarize_hop1 | 2.703 | 2.292 | 4.721 |
| query_hop2 | 0.752 | 0.710 | 1.090 |
| retrieve_hop2 | 0.822 | 0.018 | 1.624 |
| summarize_hop2 | 3.659 | 3.236 | 6.699 |
| query_hop3 | 0.877 | 0.712 | 1.592 |
| retrieve_hop3 | 0.406 | 0.002 | 1.568 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **9.227** | **8.336** | **13.749** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 74 |
