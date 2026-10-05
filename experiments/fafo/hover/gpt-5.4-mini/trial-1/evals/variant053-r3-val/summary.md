# Evaluation Summary

Total cases: 300

## Composite Score
- average: 80.00

## Score Breakdown
- num_found: 2.78
- num_gold: 3.00
- partial_recall: 92.67
- recall: 80.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.008 | 0.002 | 0.005 |
| summarize_hop1 | 3.670 | 3.083 | 6.858 |
| query_hop2 | 1.104 | 0.843 | 1.661 |
| retrieve_hop2 | 1.137 | 1.312 | 1.587 |
| summarize_hop2 | 5.318 | 4.728 | 9.635 |
| query_hop3 | 1.599 | 1.034 | 3.646 |
| retrieve_hop3 | 0.522 | 0.002 | 1.546 |
| combine_retrievals | 0.000 | 0.000 | 0.000 |
| **Total** | **13.358** | **12.296** | **23.360** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 60 |
