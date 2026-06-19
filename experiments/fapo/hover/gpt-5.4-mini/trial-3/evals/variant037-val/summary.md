# Evaluation Summary

Total cases: 300

## Composite Score
- average: 37.33

## Score Breakdown
- num_found: 2.19
- num_gold: 3.00
- num_missing: 0.81
- partial_recall: 73.00
- recall: 37.33

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.004 | 0.002 | 0.005 |
| summarize_hop1 | 1.926 | 1.732 | 2.885 |
| query_hop2 | 0.927 | 0.695 | 1.415 |
| retrieve_hop2 | 1.133 | 1.478 | 1.631 |
| summarize_hop2 | 2.200 | 2.062 | 3.513 |
| query_hop3 | 0.901 | 0.704 | 1.091 |
| retrieve_hop3 | 1.316 | 1.511 | 1.641 |
| summarize_hop3 | 2.090 | 1.917 | 3.435 |
| query_hop4 | 0.755 | 0.694 | 1.192 |
| retrieve_hop4 | 1.299 | 1.505 | 1.628 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **12.552** | **11.857** | **17.687** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop4 | 188 |
