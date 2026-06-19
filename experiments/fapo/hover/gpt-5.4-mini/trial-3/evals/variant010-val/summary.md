# Evaluation Summary

Total cases: 300

## Composite Score
- average: 23.67

## Score Breakdown
- num_found: 1.85
- num_gold: 3.00
- num_missing: 1.15
- partial_recall: 61.67
- recall: 23.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.011 | 0.002 | 0.009 |
| summarize_hop1 | 1.676 | 1.498 | 2.478 |
| query_hop2 | 0.852 | 0.740 | 1.174 |
| retrieve_hop2 | 1.138 | 1.308 | 1.637 |
| summarize_hop2 | 1.926 | 1.791 | 2.652 |
| query_hop3 | 0.853 | 0.769 | 1.061 |
| retrieve_hop3 | 1.262 | 1.498 | 1.662 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **7.717** | **7.481** | **11.840** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 229 |
