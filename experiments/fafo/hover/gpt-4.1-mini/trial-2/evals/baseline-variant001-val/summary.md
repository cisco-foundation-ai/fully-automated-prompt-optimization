# Evaluation Summary

Total cases: 300

## Composite Score
- average: 20.67

## Score Breakdown
- num_found: 1.81
- num_gold: 3.00
- partial_recall: 60.22
- recall: 20.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.003 | 0.002 | 0.004 |
| summarize_hop1 | 3.240 | 2.640 | 5.748 |
| query_hop2 | 1.005 | 0.754 | 1.709 |
| retrieve_hop2 | 1.469 | 1.453 | 1.641 |
| summarize_hop2 | 3.785 | 3.073 | 8.443 |
| query_hop3 | 0.983 | 0.812 | 1.836 |
| retrieve_hop3 | 1.207 | 1.439 | 1.663 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **11.691** | **10.445** | **22.388** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 238 |
