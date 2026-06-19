# Evaluation Summary

Total cases: 300

## Composite Score
- average: 57.67

## Score Breakdown
- num_found: 2.50
- num_gold: 3.00
- partial_recall: 83.22
- recall: 57.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.003 | 0.002 | 0.004 |
| summarize_hop1 | 6.508 | 5.276 | 11.966 |
| query_hop2 | 0.917 | 0.615 | 2.035 |
| retrieve_hop2 | 1.060 | 1.417 | 1.552 |
| summarize_hop2 | 6.386 | 5.529 | 11.889 |
| query_hop3 | 0.897 | 0.641 | 1.981 |
| retrieve_hop3 | 1.108 | 1.449 | 1.569 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **16.880** | **15.012** | **26.553** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 127 |
