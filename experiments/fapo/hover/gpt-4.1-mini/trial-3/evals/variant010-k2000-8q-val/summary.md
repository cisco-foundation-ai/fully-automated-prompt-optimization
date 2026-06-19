# Evaluation Summary

Total cases: 300

## Composite Score
- average: 94.67

## Score Breakdown
- num_found: 2.94
- num_gold: 3.00
- partial_recall: 98.11
- recall: 94.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 1.089 | 0.599 | 1.766 |
| summarize_hop1 | 23.052 | 21.272 | 38.758 |
| query_hop2 | 1.202 | 0.911 | 2.219 |
| retrieve_hop2 | 11.650 | 12.310 | 13.250 |
| summarize_hop2 | 31.587 | 24.743 | 64.965 |
| query_hop3 | 1.200 | 1.113 | 1.738 |
| retrieve_hop3 | 8.416 | 9.139 | 12.846 |
| combine_retrievals | 0.003 | 0.002 | 0.008 |
| **Total** | **78.200** | **72.420** | **116.667** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop3 | 16 |
