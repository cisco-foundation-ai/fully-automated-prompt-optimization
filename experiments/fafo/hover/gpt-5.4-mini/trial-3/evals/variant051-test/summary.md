# Evaluation Summary

Total cases: 300

## Composite Score
- average: 60.67

## Score Breakdown
- num_found: 2.54
- num_gold: 3.00
- num_missing: 0.46
- partial_recall: 84.67
- recall: 60.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.004 | 0.002 | 0.007 |
| summarize_hop1 | 3.125 | 2.655 | 5.645 |
| query_hop2 | 0.833 | 0.733 | 1.071 |
| retrieve_hop2 | 1.512 | 1.540 | 1.654 |
| summarize_hop2 | 3.411 | 3.108 | 6.207 |
| query_hop3 | 0.794 | 0.729 | 1.200 |
| retrieve_hop3 | 1.417 | 1.545 | 1.651 |
| summarize_hop3 | 3.339 | 2.857 | 6.478 |
| query_hop4 | 0.780 | 0.704 | 1.023 |
| retrieve_hop4 | 1.303 | 1.540 | 1.648 |
| combine_retrievals | 0.001 | 0.001 | 0.001 |
| **Total** | **16.519** | **15.838** | **23.426** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop4 | 118 |
