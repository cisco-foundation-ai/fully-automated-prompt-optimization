# Evaluation Summary

Total cases: 300

## Composite Score
- average: 73.33

## Score Breakdown
- num_found: 2.71
- num_gold: 3.00
- partial_recall: 90.22
- recall: 73.33

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.028 | 0.002 | 0.005 |
| summarize_hop1 | 2.317 | 2.156 | 3.795 |
| query_hop2 | 0.849 | 0.694 | 1.194 |
| retrieve_hop2 | 0.760 | 0.003 | 1.687 |
| summarize_hop2 | 3.600 | 3.096 | 6.120 |
| query_hop3 | 1.008 | 0.791 | 1.422 |
| retrieve_hop3 | 0.985 | 1.333 | 1.714 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **9.548** | **8.806** | **13.851** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 80 |
