# Evaluation Summary

Total cases: 300

## Composite Score
- average: 23.67

## Score Breakdown
- num_found: 1.84
- num_gold: 3.00
- num_missing: 1.16
- partial_recall: 61.44
- recall: 23.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.010 | 0.002 | 0.005 |
| summarize_hop1 | 1.530 | 1.447 | 2.347 |
| query_hop2 | 0.815 | 0.720 | 1.014 |
| retrieve_hop2 | 1.088 | 1.315 | 1.625 |
| summarize_hop2 | 1.972 | 1.835 | 2.622 |
| query_hop3 | 0.842 | 0.713 | 1.004 |
| retrieve_hop3 | 1.177 | 1.482 | 1.613 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **7.434** | **7.186** | **10.023** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 229 |
