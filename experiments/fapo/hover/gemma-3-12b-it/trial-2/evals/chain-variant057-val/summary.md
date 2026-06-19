# Evaluation Summary

Total cases: 300

## Composite Score
- average: 80.67

## Score Breakdown
- num_found: 2.79
- num_gold: 3.00
- num_missing: 0.21
- partial_recall: 92.89
- recall: 80.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.003 | 0.002 | 0.004 |
| summarize_hop1 | 3.170 | 2.736 | 5.712 |
| query_hop2 | 0.455 | 0.326 | 1.012 |
| retrieve_hop2 | 0.870 | 1.106 | 1.607 |
| summarize_hop2 | 7.231 | 6.133 | 10.864 |
| query_hop3 | 0.466 | 0.372 | 1.120 |
| retrieve_hop3 | 2.359 | 2.563 | 3.123 |
| summarize_hop3 | 7.687 | 7.434 | 12.611 |
| query_hop4 | 0.504 | 0.417 | 0.874 |
| retrieve_hop4 | 1.302 | 1.364 | 1.612 |
| query_hop5 | 0.565 | 0.466 | 1.116 |
| retrieve_hop5 | 2.104 | 2.453 | 3.072 |
| combine_retrievals | 0.000 | 0.000 | 0.001 |
| **Total** | **26.717** | **25.527** | **35.023** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop5 | 58 |
