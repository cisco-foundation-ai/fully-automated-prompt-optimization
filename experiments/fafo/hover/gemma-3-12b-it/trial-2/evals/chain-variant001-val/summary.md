# Evaluation Summary

Total cases: 300

## Composite Score
- average: 66.67

## Score Breakdown
- num_found: 2.63
- num_gold: 3.00
- num_missing: 0.37
- partial_recall: 87.67
- recall: 66.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.003 | 0.002 | 0.010 |
| summarize_hop1 | 3.482 | 3.019 | 7.101 |
| query_hop2 | 0.378 | 0.332 | 0.750 |
| retrieve_hop2 | 0.823 | 1.048 | 1.633 |
| summarize_hop2 | 8.431 | 7.798 | 12.763 |
| query_hop3 | 0.423 | 0.346 | 0.702 |
| retrieve_hop3 | 0.801 | 1.052 | 1.630 |
| summarize_hop3 | 12.098 | 11.006 | 18.289 |
| query_hop4 | 0.427 | 0.362 | 0.768 |
| retrieve_hop4 | 0.913 | 1.070 | 1.631 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **27.780** | **26.158** | **38.266** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop4 | 100 |
